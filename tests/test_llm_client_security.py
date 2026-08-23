from __future__ import annotations

import socket

import pytest

from zhilian_tianhe_agent.errors import ModelGatewayError
from zhilian_tianhe_agent.llm_client import LLMClient, LLMConfig


def test_rejects_plain_http(monkeypatch):
    monkeypatch.delenv("ALLOW_INSECURE_LLM_HTTP", raising=False)

    with pytest.raises(ModelGatewayError, match="HTTPS") as caught:
        LLMClient(LLMConfig(api_key="x", base_url="http://example.com/v1", model="demo"))

    assert caught.value.code == "MODEL_CONFIG_INVALID"
    assert caught.value.status_code == 400


def test_rejects_private_dns_result(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
    )

    with pytest.raises(ModelGatewayError, match="内网") as caught:
        LLMClient(LLMConfig(api_key="x", base_url="https://gateway.example/v1", model="demo"))

    assert caught.value.code == "MODEL_CONFIG_INVALID"


def test_dns_failure_is_classified(monkeypatch):
    def fail(*args, **kwargs):  # noqa: ARG001
        raise socket.gaierror("internal resolver detail")

    monkeypatch.setattr(socket, "getaddrinfo", fail)

    with pytest.raises(ModelGatewayError) as caught:
        LLMClient(LLMConfig(api_key="x", base_url="https://gateway.example/v1", model="demo"))

    assert caught.value.code == "MODEL_GATEWAY_UNREACHABLE"
    assert caught.value.retryable is True
    assert "internal resolver" not in str(caught.value)


def test_accepts_public_https(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))],
    )

    client = LLMClient(LLMConfig(api_key="x", base_url="https://gateway.example/v1", model="demo"))

    assert client.enabled
    assert client._url() == "https://gateway.example/v1/chat/completions"
