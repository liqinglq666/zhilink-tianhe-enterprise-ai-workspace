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
    encoding = "utf-8"

    def __init__(self, *, payload=None, lines=None, headers=None, raw_body: bytes | None = None):
        self._payload = payload
        self._lines = lines or []
        self.headers = headers or {}
        self.closed = False
        if raw_body is not None:
            self._raw_body = raw_body
        elif self._lines:
            self._raw_body = ("\n".join(self._lines) + "\n").encode("utf-8")
        else:
            self._raw_body = json.dumps(payload or {}).encode("utf-8")

    def iter_content(self, chunk_size=65536):
        for start in range(0, len(self._raw_body), chunk_size):
            yield self._raw_body[start : start + chunk_size]

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


def test_non_stream_wire_response_is_bounded_before_json_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_MAX_RESPONSE_BYTES", "1024")
    current = client(monkeypatch)
    response = FakeResponse(raw_body=b"{" + b"x" * 2048 + b"}")
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: response)

    with pytest.raises(ModelGatewayError) as caught:
        current.chat("system", "user")

    assert caught.value.code == "MODEL_RESPONSE_LIMIT_EXCEEDED"
    assert response.closed is True


def test_non_stream_http_body_is_always_streamed(monkeypatch: pytest.MonkeyPatch) -> None:
    current = client(monkeypatch)
    response = FakeResponse(payload={"choices": [{"message": {"content": "ok"}}]})
    captured = {}

    def fake_post(*args, **kwargs):  # noqa: ANN002, ANN003
        captured.update(kwargs)
        return response

    monkeypatch.setattr(requests, "post", fake_post)
    assert current.chat("system", "user") == "ok"
    assert captured["stream"] is True


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


def test_stream_single_line_wire_response_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_MAX_RESPONSE_BYTES", "1024")
    current = client(monkeypatch)
    response = FakeResponse(raw_body=b"data: " + b"x" * 2048)
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: response)

    with pytest.raises(ModelGatewayError) as caught:
        list(current.chat_stream("system", "user"))

    assert caught.value.code == "MODEL_RESPONSE_LIMIT_EXCEEDED"
    assert response.closed is True


def test_stream_parser_handles_sse_lines_split_across_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    current = client(monkeypatch)
    line = f"data: {json.dumps({'choices': [{'delta': {'content': 'hello'}}]})}\n"
    response = FakeResponse(raw_body=line.encode("utf-8"))
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: response)

    assert list(current.chat_stream("system", "user")) == ["hello"]
    assert response.closed is True


def test_enterprise_allowlist_can_be_required(monkeypatch: pytest.MonkeyPatch) -> None:
    public_dns(monkeypatch)
    monkeypatch.setenv("LLM_REQUIRE_HOST_ALLOWLIST", "true")
    monkeypatch.delenv("LLM_ALLOWED_HOSTS", raising=False)

    with pytest.raises(ModelGatewayError) as caught:
        LLMClient(LLMConfig(api_key="x", base_url="https://gateway.example/v1", model="demo"))

    assert caught.value.code == "MODEL_CONFIG_INVALID"
