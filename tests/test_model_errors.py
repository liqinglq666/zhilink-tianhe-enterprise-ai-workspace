from __future__ import annotations

import socket

import pytest
import requests

from zhilian_tianhe_agent.errors import ModelGatewayError
from zhilian_tianhe_agent.llm_client import LLMClient, LLMConfig


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None, lines=None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self._lines = lines or []
        self.is_redirect = 300 <= status_code < 400
        self.ok = 200 <= status_code < 300
        self.closed = False

    def close(self):
        self.closed = True

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload

    def iter_lines(self, **kwargs):  # noqa: ARG002
        yield from self._lines


def make_client(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))],
    )
    return LLMClient(LLMConfig(api_key="x", base_url="https://gateway.example/v1", model="demo"))


def test_error_payload_is_stable():
    error = ModelGatewayError(
        code="MODEL_RATE_LIMITED",
        user_message="请稍后重试。",
        status_code=429,
        retryable=True,
        retry_after=12,
    )

    assert error.to_payload() == {
        "detail": "请稍后重试。",
        "code": "MODEL_RATE_LIMITED",
        "retryable": True,
        "retry_after": 12,
    }


def test_missing_config_does_not_require_dns(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: pytest.fail("DNS should not run"))
    client = LLMClient(LLMConfig(api_key="", base_url="https://gateway.example/v1", model="demo"))

    with pytest.raises(ModelGatewayError) as caught:
        client.chat("system", "user")

    assert caught.value.code == "MODEL_NOT_CONFIGURED"
    assert caught.value.status_code == 400


def test_auth_error_is_classified(monkeypatch):
    client = make_client(monkeypatch)
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: FakeResponse(401))

    with pytest.raises(ModelGatewayError) as caught:
        client.chat("system", "user")

    assert caught.value.code == "MODEL_AUTH_FAILED"
    assert caught.value.status_code == 401
    assert "API Key" in caught.value.user_message


def test_rate_limit_includes_retry_after(monkeypatch):
    client = make_client(monkeypatch)
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: FakeResponse(429, headers={"Retry-After": "12"}),
    )

    with pytest.raises(ModelGatewayError) as caught:
        client.chat("system", "user")

    assert caught.value.code == "MODEL_RATE_LIMITED"
    assert caught.value.retry_after == 12
    assert caught.value.retryable is True


def test_timeout_is_classified_without_leaking_detail(monkeypatch):
    client = make_client(monkeypatch)

    def fail(*args, **kwargs):  # noqa: ARG001
        raise requests.Timeout("secret upstream diagnostic")

    monkeypatch.setattr(requests, "post", fail)

    with pytest.raises(ModelGatewayError) as caught:
        client.chat("system", "user")

    assert caught.value.code == "MODEL_TIMEOUT"
    assert "secret" not in str(caught.value)


def test_bad_json_is_safe(monkeypatch):
    client = make_client(monkeypatch)
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: FakeResponse(200, payload=ValueError("secret provider body")),
    )

    with pytest.raises(ModelGatewayError) as caught:
        client.chat("system", "user")

    assert caught.value.code == "MODEL_BAD_RESPONSE"
    assert "secret" not in str(caught.value)


def test_empty_stream_is_classified(monkeypatch):
    client = make_client(monkeypatch)
    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: FakeResponse(200, lines=[b"data: [DONE]"]),
    )

    with pytest.raises(ModelGatewayError) as caught:
        list(client.chat_stream("system", "user"))

    assert caught.value.code == "MODEL_EMPTY_RESPONSE"
    assert caught.value.retryable is True
