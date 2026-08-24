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


def test_browser_stream_requires_explicit_done_before_formalizing_result() -> None:
    source = Path("frontend/assets/generation-controls.js").read_text(encoding="utf-8")

    assert "let receivedDone = false;" in source
    assert 'receivedDone = true;' in source
    assert '"STREAM_INCOMPLETE"' in source
    assert "if (!receivedDone)" in source
    assert 'showStoppedResult(key, message, task.full);' in source
    assert "task.requiresVerification && !task.verified" in source
    fallback_finish = 'finishStreamingResult(key, task.full, task.verified ? "AI模型模式（已校验）" : "AI模型流式模式")'
    assert source.index("if (!receivedDone)") < source.index(fallback_finish)
