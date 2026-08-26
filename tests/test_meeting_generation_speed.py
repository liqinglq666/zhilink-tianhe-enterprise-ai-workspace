from pathlib import Path

from zhilian_tianhe_agent.agents import (
    MEETING_COMPACT_OUTPUT_RULES,
    MEETING_COMPLETION_TOKEN_LIMIT,
    MeetingAgent,
)


ROOT = Path(__file__).resolve().parents[1]


class _FakeStreamingLLM:
    def __init__(self) -> None:
        self._max_completion_tokens = 8192
        self.observed_limit = None

    def chat_stream(self, system_prompt: str, user_prompt: str):
        self.observed_limit = self._max_completion_tokens
        yield "## 一句话结论\n本次会议已形成明确复盘安排。[MT-01]\n"


def test_meeting_prompt_has_compact_output_contract():
    agent = MeetingAgent(_FakeStreamingLLM())
    prompt, _ = agent._prepare("会议确认由运营组负责复盘，并于下周提交结论。", "")

    assert MEETING_COMPLETION_TOKEN_LIMIT == 4096
    assert MEETING_COMPACT_OUTPUT_RULES in prompt
    assert "正文默认控制在约 1800–2500 个中文字符" in prompt
    assert "不要在正文重复抄写完整会议原文或证据摘录" in prompt


def test_meeting_stream_temporarily_caps_completion_budget_and_restores_it():
    llm = _FakeStreamingLLM()
    agent = MeetingAgent(llm)

    events = list(agent.stream_events("会议确认由运营组负责复盘，并于下周提交结论。"))

    assert llm.observed_limit == MEETING_COMPLETION_TOKEN_LIMIT
    assert llm._max_completion_tokens == 8192
    assert [event.type for event in events] == ["delta", "verifying", "verified"]


def test_generation_ui_reports_elapsed_time_and_received_characters():
    source = (ROOT / "frontend" / "assets" / "generation-controls.js").read_text(encoding="utf-8")

    assert "startedAt: Date.now()" in source
    assert 'phase: "connecting"' in source
    assert "setInterval(() => updateGenerationProgress(key, task), 1000)" in source
    assert "已接收约 ${chars.toLocaleString()} 字 · ${seconds} 秒" in source
    assert "正在核对事实与证据" in source
