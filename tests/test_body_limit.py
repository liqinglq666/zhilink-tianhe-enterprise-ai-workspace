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


def test_replayed_body_is_delivered_once():
    receive = replay_body(b"payload")

    first = asyncio.run(receive())
    second = asyncio.run(receive())

    assert first["body"] == b"payload"
    assert second["body"] == b""
