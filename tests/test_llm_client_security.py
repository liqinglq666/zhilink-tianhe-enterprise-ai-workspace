from __future__ import annotations

import socket

import pytest

from zhilian_tianhe_agent.llm_client import LLMClient, LLMConfig


def test_rejects_plain_http(monkeypatch):
    monkeypatch.delenv("ALLOW_INSECURE_LLM_HTTP", raising=False)

    with pytest.raises(RuntimeError, match="HTTPS"):
        LLMClient(LLMConfig(api_key="x", base_url="http://example.com/v1", model="demo"))


def test_rejects_private_dns_result(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
    )

    with pytest.raises(RuntimeError, match="内网"):
        LLMClient(LLMConfig(api_key="x", base_url="https://gateway.example/v1", model="demo"))


def test_accepts_public_https(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))],
    )

    client = LLMClient(LLMConfig(api_key="x", base_url="https://gateway.example/v1", model="demo"))

    assert client.enabled
    assert client._url() == "https://gateway.example/v1/chat/completions"
