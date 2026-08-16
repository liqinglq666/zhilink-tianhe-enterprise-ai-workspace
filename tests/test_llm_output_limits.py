from __future__ import annotations

import json
import socket

import pytest
import requests

from zhilian_tianhe_agent.errors import ModelGatewayError
from zhilian_tianhe_agent.llm_client import LLMClient, LLMConfig


class FakeResponse:
    status_code = 200
    ok = True
    is_redirect = False

    def __init__(self, *, payload=None, lines=None, headers=None):
        self._payload = payload
        self._lines = lines or []
        self.headers = headers or {}
        self.closed = False

    def json(self):
        return self._payload

    def iter_lines(self, **kwargs):  # noqa: ARG002
        yield from self._lines

    def close(self):
        self.closed = True


def public_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))],
    )


def client(monkeypatch: pytest.MonkeyPatch) -> LLMClient:
    public_dns(monkeypatch)
    return LLMClient(LLMConfig(api_key="x", base_url="https://gateway.example/v1", model="demo"))


def test_payload_sets_completion_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_MAX_COMPLETION_TOKENS", "4096")
    current = client(monkeypatch)
    assert current._payload("system", "user")["max_tokens"] == 4096


def test_non_stream_output_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_MAX_OUTPUT_CHARS", "1000")
    current = client(monkeypatch)
    response = FakeResponse(payload={"choices": [{"message": {"content": "x" * 1001}}]})
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: response)

    with pytest.raises(ModelGatewayError) as caught:
        current.chat("system", "user")

    assert caught.value.code == "MODEL_OUTPUT_LIMIT_EXCEEDED"
    assert response.closed is True


def test_stream_output_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_MAX_OUTPUT_CHARS", "1000")
    current = client(monkeypatch)
    lines = [
        f"data: {json.dumps({'choices': [{'delta': {'content': 'x' * 600}}]})}",
        f"data: {json.dumps({'choices': [{'delta': {'content': 'y' * 600}}]})}",
    ]
    response = FakeResponse(lines=lines)
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: response)

    with pytest.raises(ModelGatewayError) as caught:
        list(current.chat_stream("system", "user"))

    assert caught.value.code == "MODEL_OUTPUT_LIMIT_EXCEEDED"
    assert response.closed is True


def test_enterprise_allowlist_can_be_required(monkeypatch: pytest.MonkeyPatch) -> None:
    public_dns(monkeypatch)
    monkeypatch.setenv("LLM_REQUIRE_HOST_ALLOWLIST", "true")
    monkeypatch.delenv("LLM_ALLOWED_HOSTS", raising=False)

    with pytest.raises(ModelGatewayError) as caught:
        LLMClient(LLMConfig(api_key="x", base_url="https://gateway.example/v1", model="demo"))

    assert caught.value.code == "MODEL_CONFIG_INVALID"
