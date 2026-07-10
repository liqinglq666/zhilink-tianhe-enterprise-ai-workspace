from __future__ import annotations

import asyncio
import socket
from pathlib import Path

import pytest
import requests
from fastapi.testclient import TestClient

from backend.main import _stream_response, app
from zhilian_tianhe_agent.llm_client import LLMClient, LLMConfig


client = TestClient(app)
ROOT = Path(__file__).resolve().parents[1]


class _FakeStreamResponse:
    is_redirect = False
    ok = True
    encoding = None

    def __init__(self, lines: list[str | bytes]):
        self._lines = lines

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):  # noqa: ARG002
        return False

    def iter_lines(self, decode_unicode=True):  # noqa: ARG002
        yield from self._lines


class _InterruptedStreamResponse(_FakeStreamResponse):
    def iter_lines(self, decode_unicode=True):  # noqa: ARG002
        yield from self._lines
        raise requests.exceptions.ChunkedEncodingError("incomplete chunk")


class _FakeJsonResponse:
    is_redirect = False
    ok = True

    def __init__(self, payload: dict):
        self._payload = payload

    def json(self):
        return self._payload



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



def _configured_client() -> LLMClient:
    llm = LLMClient(
        LLMConfig(
            api_key="test-key",
            base_url="https://gateway.example/v1",
            model="test-model",
        )
    )
    llm._base_url = "https://gateway.example/v1"
    return llm



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



def test_upstream_eof_after_content_is_accepted(monkeypatch):
    response = _FakeStreamResponse(
        ['data: {"choices":[{"delta":{"content":"完整"}}]}']
    )
    monkeypatch.setattr(
        "zhilian_tianhe_agent.llm_client.requests.post",
        lambda *args, **kwargs: response,
    )

    assert list(_configured_client().chat_stream("system", "user")) == ["完整"]



def test_upstream_transport_interruption_is_rejected(monkeypatch):
    response = _InterruptedStreamResponse(
        ['data: {"choices":[{"delta":{"content":"partial"}}]}']
    )
    monkeypatch.setattr(
        "zhilian_tianhe_agent.llm_client.requests.post",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(RuntimeError, match="异常中断"):
        list(_configured_client().chat_stream("system", "user"))



def test_upstream_finish_reason_completes_stream(monkeypatch):
    response = _FakeStreamResponse(
        [
            'data: {"choices":[{"delta":{"content":"完整"}}]}',
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}',
        ]
    )
    monkeypatch.setattr(
        "zhilian_tianhe_agent.llm_client.requests.post",
        lambda *args, **kwargs: response,
    )

    assert list(_configured_client().chat_stream("system", "user")) == ["完整"]



def test_dashscope_nested_output_stream_is_supported(monkeypatch):
    response = _FakeStreamResponse(
        ['data: {"output":{"choices":[{"message":{"content":"嵌套格式内容"}}]}}']
    )
    monkeypatch.setattr(
        "zhilian_tianhe_agent.llm_client.requests.post",
        lambda *args, **kwargs: response,
    )

    assert list(_configured_client().chat_stream("system", "user")) == ["嵌套格式内容"]



def test_cumulative_stream_only_emits_new_suffix(monkeypatch):
    response = _FakeStreamResponse(
        [
            'data: {"output":{"text":"会"}}',
            'data: {"output":{"text":"会议"}}',
            'data: {"output":{"text":"会议纪要"}}',
        ]
    )
    monkeypatch.setattr(
        "zhilian_tianhe_agent.llm_client.requests.post",
        lambda *args, **kwargs: response,
    )

    assert list(_configured_client().chat_stream("system", "user")) == ["会", "议", "纪要"]



def test_empty_stream_falls_back_to_non_streaming_response(monkeypatch):
    responses = iter(
        [
            _FakeStreamResponse(['data: {"choices":[{"delta":{}}]}', "data: [DONE]"]),
            _FakeJsonResponse({"choices": [{"message": {"content": "非流式回退结果"}}]}),
        ]
    )
    monkeypatch.setattr(
        "zhilian_tianhe_agent.llm_client.requests.post",
        lambda *args, **kwargs: next(responses),
    )

    assert list(_configured_client().chat_stream("system", "user")) == ["非流式回退结果"]



def test_non_streaming_content_blocks_are_supported(monkeypatch):
    response = _FakeJsonResponse(
        {"choices": [{"message": {"content": [{"type": "text", "text": "分块文本"}]}}]}
    )
    monkeypatch.setattr(
        "zhilian_tianhe_agent.llm_client.requests.post",
        lambda *args, **kwargs: response,
    )

    assert _configured_client().chat("system", "user") == "分块文本"



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



def test_frontend_accepts_clean_eof_after_valid_deltas():
    script = (ROOT / "frontend" / "assets" / "bugfixes.js").read_text(encoding="utf-8")

    assert "let reachedCleanEof = false;" in script
    assert "reachedCleanEof = true;" in script
    assert "AI模型兼容流式模式" in script
    assert "模型连接提前中断，未收到完整结束事件" not in script



def test_report_export_does_not_require_model_configuration():
    resp = client.post(
        "/api/report/txt",
        json={"results": {"会议纪要": "测试内容"}},
    )

    assert resp.status_code == 200
    assert "测试内容" in resp.text
