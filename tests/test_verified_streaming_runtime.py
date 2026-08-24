from __future__ import annotations

import asyncio
from pathlib import Path

from backend import main
from zhilian_tianhe_agent.agents import AgentStreamEvent, ContractAgent, MeetingAgent
from zhilian_tianhe_agent.llm_client import LLMClient, LLMConfig


class FakeLLM:
    def chat_stream(self, system_prompt: str, user_prompt: str):  # noqa: ARG002
        yield "## 一句话结论\n"
        yield "已形成可供校验的草稿。\n"


class ClosableChunks:
    def __init__(self) -> None:
        self.sent = False
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self):
        if self.sent:
            raise StopIteration
        self.sent = True
        return "partial"

    def close(self) -> None:
        self.closed = True


class DummyResponse:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_meeting_stream_events_expose_draft_before_verified_result() -> None:
    agent = MeetingAgent(FakeLLM())
    events = list(agent.stream_events("会议决定由运营组继续跟进材料整理。", ""))

    assert events[0].type == "delta"
    assert any(event.type == "verifying" for event in events)
    assert events[-1].type == "verified"
    assert events[-1].content.strip()
    assert events[-1].mode == "AI模型模式（已事实校验）"


def test_contract_stream_events_expose_draft_before_verified_result() -> None:
    agent = ContractAgent(FakeLLM())
    events = list(agent.stream_events("付款条款：验收后按合同约定支付。交付范围以双方书面确认为准。", ""))

    assert events[0].type == "delta"
    assert any(event.type == "verifying" for event in events)
    assert events[-1].type == "verified"
    assert events[-1].content.strip()
    assert "本地规则" in events[-1].mode


def test_verified_sse_requires_and_emits_verified_replacement() -> None:
    events = iter(
        [
            AgentStreamEvent(type="delta", content="draft"),
            AgentStreamEvent(type="verifying"),
            AgentStreamEvent(type="verified", content="verified", mode="verified-mode"),
        ]
    )

    async def exercise() -> str:
        response = main._verified_stream_response(events)
        output = []
        async for chunk in response.body_iterator:
            output.append(chunk)
        return "".join(output)

    payload = asyncio.run(exercise())

    assert '"provisional": true' in payload
    assert '"type": "delta"' in payload
    assert '"type": "verifying"' in payload
    assert '"type": "verified"' in payload
    assert payload.index('"type": "delta"') < payload.index('"type": "verified"') < payload.index('"type": "done"')


def test_stream_close_invokes_upstream_cancellation_before_release() -> None:
    chunks = ClosableChunks()
    cancelled = []

    async def exercise() -> None:
        response = main._stream_response(chunks, cancel_callback=lambda: cancelled.append(True))
        stream = response.body_iterator
        await anext(stream)
        await stream.aclose()

    asyncio.run(exercise())

    assert cancelled == [True]
    assert chunks.closed is True


def test_llm_client_can_close_active_upstream_response() -> None:
    client = LLMClient(LLMConfig(api_key="", base_url="", model=""))
    response = DummyResponse()

    client._track_response(response)  # type: ignore[arg-type]
    client.cancel_active_requests()

    assert response.closed is True
    assert client._active_responses == {}


def test_browser_transport_handles_verified_stream_without_exposing_transport_details() -> None:
    source = Path("frontend/assets/generation-controls.js").read_text(encoding="utf-8")

    assert 'event.type === "verifying"' in source
    assert 'event.type === "verified"' in source
    assert "task.requiresVerification" in source
    assert "task.verified" in source
    assert "idle_timeout_ms" in source
    assert "hard_timeout_ms" in source
    assert '<span class="meta-pill">AI模型流式模式</span>' not in source
    assert "连接超时 30 秒" not in source
    assert "生成超时由服务端协调" not in source
    assert "正在连接模型接口" not in source
    assert "流式生成中" not in source
    assert "正在核对内容" in source


def test_meeting_and_contract_routes_use_verified_stream_protocol() -> None:
    source = Path("backend/main.py").read_text(encoding="utf-8")

    assert "hub.meeting.stream_events" in source
    assert "hub.contract.stream_events" in source
    assert "cancel_callback=hub.llm.cancel_active_requests" in source
