from __future__ import annotations

from collections.abc import Awaitable, Callable

Receive = Callable[[], Awaitable[dict]]


class BodyTooLarge(ValueError):
    pass


async def read_limited_body(receive: Receive, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    size = 0

    while True:
        message = await receive()
        if message.get("type") == "http.disconnect":
            break
        if message.get("type") != "http.request":
            continue

        chunk = message.get("body", b"")
        size += len(chunk)
        if size > max_bytes:
            raise BodyTooLarge
        if chunk:
            chunks.append(chunk)
        if not message.get("more_body", False):
            break

    return b"".join(chunks)


def replay_body(body: bytes) -> Receive:
    sent = False

    async def receive() -> dict:
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive
