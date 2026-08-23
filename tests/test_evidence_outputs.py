from __future__ import annotations

from zhilian_tianhe_agent.agents import (
    LandingAgent,
    MatchAgent,
    MeetingAgent,
    PolicyAgent,
    ProfileAgent,
    ReportAgent,
)
from zhilian_tianhe_agent.evidence import (
    MAX_EXCERPT_CHARS,
    build_landing_evidence,
    build_match_evidence,
    build_meeting_evidence,
    build_policy_evidence,
    build_profile_evidence,
    build_report_evidence,
)


class FakeLLM:
    def __init__(self):
        self.prompts: list[str] = []

    def chat(self, system_prompt: str, user_prompt: str) -> str:  # noqa: ARG002
        self.prompts.append(user_prompt)
        return "## 一句话结论\n这是基于输入的 AI 推断。"

    def chat_stream(self, system_prompt: str, user_prompt: str):  # noqa: ARG002
        self.prompts.append(user_prompt)
        yield "## 一句话结论\n"
        yield "这是基于输入的 AI 推断。"


def test_profile_bundle_indexes_inputs_and_missing_fields():
    bundle = build_profile_evidence(
        {"name": "测试企业", "industry": "", "demands": "需要合同审阅"}
    )

    assert bundle.evidence[0].evidence_id == "PF-01"
    assert any(item.field == "当前需求" for item in bundle.evidence)
    assert any("所属行业" in item.question for item in bundle.pending_confirmations)
    assert "AI 推断" in bundle.to_markdown()


def test_meeting_bundle_extracts_bounded_evidence_and_confirmation_gaps():
    text = "讨论了活动方案。初步决定继续推进。" + ("很长的补充内容" * 100)
    bundle = build_meeting_evidence(text)

    assert bundle.evidence
    assert all(len(item.excerpt) <= MAX_EXCERPT_CHARS for item in bundle.evidence)
    assert any("截止时间" in item.question for item in bundle.pending_confirmations)
    assert any("负责人" in item.question for item in bundle.pending_confirmations)


def test_policy_bundle_distinguishes_local_reference_from_official_policy():
    bundle = build_policy_evidence(
        {"industry": "人工智能", "location": "天河区"},
        "希望了解数字化转型方向",
        [{"direction": "人工智能与大模型应用"}],
    )

    reference = next(item for item in bundle.evidence if item.evidence_id == "PR-01")
    assert reference.source_type == "本地参考"
    assert any("官方原文" in item.question for item in bundle.pending_confirmations)
    assert "不是实时政策检索结果" in bundle.limitations


def test_match_landing_and_report_bundles_keep_unknowns_pending():
    match_bundle = build_match_evidence({}, "可提供场地", "", "", "")
    assert any("需求优先级" in item.question for item in match_bundle.pending_confirmations)

    landing_bundle = build_landing_evidence(
        {},
        {"pilot_scene": "企业服务窗口试点"},
        {"会议纪要": ""},
    )
    assert any("数据范围" in item.question for item in landing_bundle.pending_confirmations)
    assert any("既有模块结果" in item.question for item in landing_bundle.pending_confirmations)

    report_bundle = build_report_evidence({"会议纪要": "已生成", "合同审阅": ""})
    assert any("合同审阅" in item.question for item in report_bundle.pending_confirmations)


def test_agents_inject_evidence_ids_and_append_deterministic_index(monkeypatch):
    monkeypatch.setattr(
        "zhilian_tianhe_agent.agents.load_json",
        lambda name: (
            {"tianhe_context": ["天河企业服务场景"]}
            if name == "tianhe_knowledge.json"
            else [{"direction": "人工智能与大模型应用"}]
        ),
    )
    cases = [
        (
            ProfileAgent,
            lambda agent: agent.run({"name": "测试企业", "demands": "需要会议协同"}),
            "PF-01",
        ),
        (
            MeetingAgent,
            lambda agent: agent.run("会议决定由张三负责跟进，下周完成。"),
            "MT-01",
        ),
        (
            PolicyAgent,
            lambda agent: agent.run({"industry": "人工智能"}, "了解政策方向"),
            "PL-01",
        ),
        (
            MatchAgent,
            lambda agent: agent.run({}, "可提供场地", "需要AI服务", "AI服务商", "试点"),
            "MO-01",
        ),
        (
            LandingAgent,
            lambda agent: agent.run(
                {},
                {"pilot_scene": "企业服务窗口试点", "data_scope": "脱敏咨询记录"},
                {"会议纪要": "已形成任务清单"},
            ),
            "LC-01",
        ),
        (
            ReportAgent,
            lambda agent: agent.run({"会议纪要": "已形成任务清单"}),
            "RP-01",
        ),
    ]

    for agent_type, invoke, evidence_id in cases:
        llm = FakeLLM()
        result = invoke(agent_type(llm))

        assert evidence_id in llm.prompts[0]
        assert "## 输入证据与待确认索引" in result.content
        assert result.mode == "AI模型模式（含证据索引）"


def test_streaming_agents_append_index_after_model_output():
    llm = FakeLLM()
    content = "".join(
        MeetingAgent(llm).stream("会议决定继续推进，但负责人和时间待定。")
    )

    assert content.startswith("## 一句话结论")
    assert "## 输入证据与待确认索引" in content
    assert "MT-01" in content
