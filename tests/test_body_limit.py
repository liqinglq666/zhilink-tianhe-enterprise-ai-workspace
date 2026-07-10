from __future__ import annotations

import asyncio

import pytest

from backend.body_limit import BodyTooLarge, read_limited_body, replay_body


def _receiver(messages):
    queue = list(messages)

    async def receive():
        return queue.pop(0)

    return receive


def test_chunked_body_is_counted_without_content_length():
    receive = _receiver(
        [
            {"type": "http.request", "body": b"1234", "more_body": True},
            {"type": "http.request", "body": b"5678", "more_body": False},
        ]
    )

    with pytest.raises(BodyTooLarge):
        asyncio.run(read_limited_body(receive, max_bytes=7))


def test_replayed_body_is_delivered_once_then_delegates_upstream():
    upstream = _receiver([{"type": "http.disconnect"}])
    receive = replay_body(b"payload", upstream)

    first = asyncio.run(receive())
    second = asyncio.run(receive())

    assert first == {"type": "http.request", "body": b"payload", "more_body": False}
    assert second == {"type": "http.disconnect"}


def test_replay_does_not_generate_endless_empty_http_requests():
    calls = 0

    async def upstream():
        nonlocal calls
        calls += 1
        return {"type": "http.disconnect"}

    receive = replay_body(b"payload", upstream)
    asyncio.run(receive())
    asyncio.run(receive())

    assert calls == 1
