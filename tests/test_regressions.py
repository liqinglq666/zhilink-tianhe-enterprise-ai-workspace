from __future__ import annotations

import asyncio
import socket

import pytest
from fastapi.testclient import TestClient

from backend.main import _stream_response, app
from zhilian_tianhe_agent.llm_client import LLMClient, LLMConfig


client = TestClient(app)


def _consume_stream(response) -> str:
    async def consume() -> str:
        chunks: list[str] = []
        async for chunk in response.body_iterator:
            if isinstance(chunk, bytes):
                chunks.append(chunk.decode("utf-8"))
            else:
                chunks.append(str(chunk))
        return "".join(chunks)

    return asyncio.run(consume())


def test_missing_api_key_does_not_trigger_dns(monkeypatch):
    def fail_dns(*args, **kwargs):  # noqa: ARG001
        raise AssertionError("DNS resolution must not run before required fields are validated")

    monkeypatch.setattr(socket, "getaddrinfo", fail_dns)
    llm = LLMClient(
        LLMConfig(
            api_key="",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen-plus",
        )
    )

    assert llm.enabled is False
    with pytest.raises(RuntimeError, match="API Key"):
        llm.chat("system", "user")


def test_empty_stream_emits_error_without_done_event():
    payload = _consume_stream(_stream_response(iter([])))

    assert '"type": "error"' in payload
    assert '"type": "done"' not in payload


def test_non_empty_stream_emits_done_event():
    payload = _consume_stream(_stream_response(iter(["有效内容"])))

    assert '"type": "delta"' in payload
    assert '"type": "done"' in payload
    assert "有效内容" in payload


def test_frontend_safeguards_are_loaded_before_and_after_app_script():
    resp = client.get("/")

    assert resp.status_code == 200
    assert '<script src="/assets/bugfixes.js" data-phase="pre"></script>' in resp.text
    assert '<script src="/assets/bugfixes.js" data-phase="post"></script>' in resp.text
    assert resp.text.index('data-phase="pre"') < resp.text.index('src="/assets/app.js"')
    assert resp.text.index('src="/assets/app.js"') < resp.text.index('data-phase="post"')


def test_report_export_does_not_require_model_configuration():
    resp = client.post(
        "/api/report/txt",
        json={"results": {"会议纪要": "测试内容"}},
    )

    assert resp.status_code == 200
    assert "测试内容" in resp.text
