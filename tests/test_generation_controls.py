from __future__ import annotations

import asyncio
from pathlib import Path

from backend import main
from backend.service import model_request_timeout_seconds


class ClosableChunks:
    def __init__(self):
        self.sent = False
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self):
        if self.sent:
            raise StopIteration
        self.sent = True
        return "partial"

    def close(self):
        self.closed = True


class RecordingLimiter:
    def __init__(self):
        self.released = []

    def release(self, key):
        self.released.append(key)


def test_model_request_timeout_is_bounded(monkeypatch):
    monkeypatch.setenv("MODEL_REQUEST_TIMEOUT_SECONDS", "3")
    assert model_request_timeout_seconds() == 10

    monkeypatch.setenv("MODEL_REQUEST_TIMEOUT_SECONDS", "900")
    assert model_request_timeout_seconds() == 600

    monkeypatch.setenv("MODEL_REQUEST_TIMEOUT_SECONDS", "invalid")
    assert model_request_timeout_seconds() == 120


def test_immediate_stream_close_closes_upstream_and_releases_slot(monkeypatch):
    chunks = ClosableChunks()
    limiter = RecordingLimiter()
    monkeypatch.setattr(main, "GENERATION_LIMITER", limiter)

    async def exercise():
        response = main._stream_response(chunks, release_key="client-1")
        stream = response.body_iterator
        meta = await anext(stream)
        assert '"type": "meta"' in meta
        await stream.aclose()

    asyncio.run(exercise())

    assert chunks.closed is True
    assert limiter.released == ["client-1"]


def test_generation_controls_are_the_only_browser_stream_transport_owner() -> None:
    app = Path("frontend/assets/app.js").read_text(encoding="utf-8")
    source = Path("frontend/assets/generation-controls.js").read_text(encoding="utf-8")

    fallback_start = app.index("async function apiStream()")
    fallback_end = app.index("function loadResultsFromSession", fallback_start)
    fallback = app[fallback_start:fallback_end]

    assert 'throw new Error("生成控制器未就绪，请刷新页面后重试。")' in fallback
    assert "fetch(" not in fallback
    assert "getReader(" not in fallback
    assert "TextDecoder" not in fallback
    assert "beginStreamingResult" not in app
    assert "downloadTextFile" not in app

    assert "function beginStreamingResult(key)" in source
    assert "beginStreamingResult = function" not in source
    assert "hooks.setGenerationTransport(runGeneration)" in source
    assert "resp.body.getReader()" in source


def test_browser_stream_only_formalizes_on_explicit_done_event() -> None:
    source = Path("frontend/assets/generation-controls.js").read_text(encoding="utf-8")

    done_start = source.index('event.type === "done"')
    error_start = source.index('event.type === "error"')
    done_block = source[done_start:error_start]

    assert 'finishStreamingResult(key, task.full, event.mode ||' in done_block
    assert 'return { ok: true, content: task.full' in done_block
    assert '"STREAM_INCOMPLETE"' in source
    assert "let receivedDone = false;" not in source
    assert "receivedDone = true;" not in source
    fallback_finish = 'finishStreamingResult(key, task.full, task.verified ? "AI模型模式（已校验）" : "AI模型流式模式")'
    assert fallback_finish not in source


def test_stopped_result_renderer_does_not_accept_discarded_partial_content() -> None:
    source = Path("frontend/assets/generation-controls.js").read_text(encoding="utf-8")

    assert "function showStoppedResult(key, message)" in source
    assert "partialContent" not in source
    assert "showStoppedResult(key, message, task.full)" not in source
    assert "showStoppedResult(key, message);" in source


def test_streaming_content_renders_once_per_non_terminal_network_chunk() -> None:
    source = Path("frontend/assets/generation-controls.js").read_text(encoding="utf-8")

    assert "lastRender" not in source
    assert "Date.now()" not in source
    assert source.count("updateStreamingResult(key, task.full);") == 1


def test_generation_transport_does_not_implicitly_save_model_config() -> None:
    source = Path("frontend/assets/generation-controls.js").read_text(encoding="utf-8")

    assert "saveConfig();" not in source
    assert "requireApiConfig" not in source


def test_generation_task_registry_stays_private_to_transport_module() -> None:
    source = Path("frontend/assets/generation-controls.js").read_text(encoding="utf-8")

    assert "const activeGenerations = new Map();" in source
    assert "activeGenerations.set(key, task);" in source
    assert "activeGenerations.get(key)" in source
    assert "activeGenerations.clear();" in source
    assert "window.__activeGenerations" not in source
