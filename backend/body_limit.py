from __future__ import annotations

from collections.abc import Awaitable, Callable

Receive = Callable[[], Awaitable[dict]]


class BodyTooLarge(ValueError):
    pass


async def read_limited_body(receive: Receive, max_bytes: int) -> bytes:
    """Read an ASGI request body while enforcing a byte limit."""

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


def replay_body(body: bytes, upstream_receive: Receive) -> Receive:
    """Replay the consumed body once, then delegate to the real ASGI receiver.

    Delegating after the replay is essential for streaming responses. Returning
    an endless sequence of empty ``http.request`` messages makes Starlette's
    disconnect listener spin forever and can starve ``StreamingResponse``.
    """

    sent = False

    async def receive() -> dict:
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}
        return await upstream_receive()

    return receive
