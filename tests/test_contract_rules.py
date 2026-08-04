from __future__ import annotations

from zhilian_tianhe_agent.agents import ContractAgent
from zhilian_tianhe_agent.contract_rules import (
    MAX_EVIDENCE_CHARS,
    load_contract_rules,
    scan_contract_rules,
)


def test_rule_library_has_unique_stable_ids():
    rules = load_contract_rules()

    assert len(rules) == 6
    assert len({rule.rule_id for rule in rules}) == len(rules)
    assert all(rule.confirm_questions for rule in rules)


def test_scan_returns_exact_evidence_and_high_risk_matches():
    text = (
        "费用与结算：服务费以后续通知为准，结算周期可根据实际情况适当顺延。\n"
        "宣传成果及全部素材归甲方所有。\n"
        "活动数据可用于后续营销和合作推广，甲方不承担赔偿责任。"
    )

    scan = scan_contract_rules(text)
    matches = {item.rule_id: item for item in scan.matches}

    assert matches["CR-PAYMENT"].severity == "高"
    assert matches["CR-IP"].severity == "高"
    assert matches["CR-DATA"].severity == "高"
    assert matches["CR-BREACH"].severity == "高"
    assert "以后续通知为准" in " ".join(matches["CR-PAYMENT"].evidence)
    assert all(
        len(value) <= MAX_EVIDENCE_CHARS
        for item in scan.matches
        for value in item.evidence
    )


def test_uncovered_rules_are_pending_confirmation_not_declared_missing():
    scan = scan_contract_rules("付款金额为一万元。")
    payload = scan.to_prompt_dict()

    assert payload["scan_type"] == "deterministic_local_keyword_scan"
    assert payload["not_located_categories"]
    assert "未命中不等于" in payload["limitations"]


def test_markdown_contains_rule_ids_evidence_and_pending_items():
    scan = scan_contract_rules("乙方支付全部费用，数据可用于模型训练。")
    markdown = scan.to_markdown()

    assert "## 本地规则预检明细" in markdown
    assert "CR-PAYMENT" in markdown
    assert "CR-DATA" in markdown
    assert "原文证据" in markdown
    assert "### 待确认信息" in markdown


def test_contract_agent_injects_scan_and_appends_deterministic_evidence():
    class FakeLLM:
        def __init__(self):
            self.prompts: list[str] = []

        def chat(self, system_prompt: str, user_prompt: str) -> str:  # noqa: ARG002
            self.prompts.append(user_prompt)
            return "## 一句话结论\n需要修改付款条款。"

        def chat_stream(self, system_prompt: str, user_prompt: str):  # noqa: ARG002
            self.prompts.append(user_prompt)
            yield "## 一句话结论\n"
            yield "需要修改付款条款。"

    llm = FakeLLM()
    agent = ContractAgent(llm)

    result = agent.run("服务费以后续通知为准，活动数据可用于模型训练。")

    assert "CR-PAYMENT" in llm.prompts[0]
    assert "CR-DATA" in llm.prompts[0]
    assert "## 本地规则预检明细" in result.content
    assert result.mode == "AI模型模式（含本地规则预检）"

    streamed = "".join(agent.stream("服务费以后续通知为准。"))
    assert "## 本地规则预检明细" in streamed
    assert "CR-PAYMENT" in streamed
