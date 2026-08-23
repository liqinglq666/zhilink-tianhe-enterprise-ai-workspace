from __future__ import annotations

from zhilian_tianhe_agent.agents import ContractAgent
from zhilian_tianhe_agent.contract_quality import audit_contract_output
from zhilian_tianhe_agent.contract_rules import scan_contract_rules


class FakeContractLLM:
    def __init__(self, content: str):
        self.content = content
        self.prompts: list[str] = []

    def chat(self, system_prompt: str, user_prompt: str) -> str:  # noqa: ARG002
        self.prompts.append(user_prompt)
        return self.content

    def chat_stream(self, system_prompt: str, user_prompt: str):  # noqa: ARG002
        self.prompts.append(user_prompt)
        midpoint = max(1, len(self.content) // 2)
        yield self.content[:midpoint]
        yield self.content[midpoint:]


def test_delivery_rule_is_not_triggered_by_generic_delay_only():
    scan = scan_contract_rules("活动如遇天气可能延期，双方另行沟通活动日期。")

    matched_ids = {item.rule_id for item in scan.matches}
    assert "CR-DELIVERY" not in matched_ids


def test_data_rule_prefers_only_the_actual_data_use_clause():
    text = (
        "结算期间如存在数据核对可适当顺延。\n"
        "活动报告包含汇总数据。\n"
        "五、数据使用：甲方可收集会员信息并用于后续营销和合作推广。"
    )
    scan = scan_contract_rules(text)
    match = next(item for item in scan.matches if item.rule_id == "CR-DATA")

    assert "后续营销" in match.evidence[0]
    assert all("数据核对" not in evidence for evidence in match.evidence)
    assert all("汇总数据" not in evidence for evidence in match.evidence)
    assert match.severity == "高"


def test_local_scan_uses_attention_language_instead_of_legal_conclusion():
    scan = scan_contract_rules(
        "若甲方因活动调整导致乙方收益低于预期，甲方不承担赔偿责任。"
    )

    prompt = scan.to_prompt_dict()
    markdown = scan.to_markdown()

    assert prompt["scan_type"] == "deterministic_local_keyword_attention_scan"
    assert "high_attention_matches" in prompt["summary"]
    assert "high_risk_matches" not in prompt["summary"]
    assert "local_attention_level" in prompt["matches"][0]
    assert "规则库高关注提示" in markdown
    assert "规则库关注级别不是法律风险结论" in markdown
    assert "本地高风险命中" not in markdown


def test_contract_audit_preserves_source_value_and_removes_invented_values():
    contract = "结算周期为活动结束后30个工作日内完成。"
    scan = scan_contract_rules(contract)
    model_output = """## 重点风险清单

| 风险等级 | 规则编号与类别 | 原文证据 | AI 判断 | 修改建议 | 待确认信息 |
|---|---|---|---|---|---|
| 高 | CR-PAYMENT | 30个工作日 | AI 推断 | 保留30个工作日，并增加5个工作日通知期及20%责任上限。 | 待确认 |

## 建议补充条款

- 约定活动结束满6个月后删除数据。

## 签约前检查清单

- [ ] 须设置3日整改期和500元补偿阈值。
"""

    checked = audit_contract_output(model_output, contract, scan)

    assert "30个工作日" in checked
    assert "5个工作日" not in checked
    assert "20%" not in checked
    assert "6个月" not in checked
    assert "3日" not in checked
    assert "500元" not in checked
    assert "【具体数值待双方协商】" in checked
    assert "## 自动一致性校验" in checked


def test_contract_audit_softens_overclaims_and_invented_rights():
    contract = (
        "甲方可使用乙方Logo用于本次活动宣传。"
        "活动成果归甲方所有。"
        "甲方可根据活动运营需要进行后续营销。"
    )
    scan = scan_contract_rules(contract)
    model_output = """## 一句话结论
当前合同最需优先处理数据风险。

## 风险总览

| 项目 | 数值 |
|---|---|
| 本地高风险命中数 | 2 |
| 本地命中类别数 | 3 |

## 重点风险清单

| 风险等级 | 规则编号与类别 | 原文证据 | AI 判断 | 修改建议 | 待确认信息 |
|---|---|---|---|---|---|
| 高 | CR-DATA | 后续营销 | 本地高风险命中成立，AI 维持高风险 | 明确禁止用于模型训练、跨项目营销或第三方共享。 | 待确认 |

## 建议补充条款

- 乙方Logo仅授予本次活动期间、天河路商圈范围内非独占性宣传使用权。
- 乙方享有署名权及同等条件下优先续约权。
- 甲方委托创作成果著作权归甲方所有。
- 乙方有权退出并获已发生费用结算。
"""

    checked = audit_contract_output(model_output, contract, scan)

    assert "AI 初步判断：" in checked
    assert "规则库高关注提示数" in checked
    assert "规则库关注类别数" in checked
    assert "本地高风险命中" not in checked
    assert "AI 维持高风险" not in checked
    assert "禁止用于模型训练" not in checked
    assert "非独占性宣传使用权" not in checked
    assert "优先续约权" not in checked
    assert "著作权归甲方所有" not in checked
    assert "有权退出并获" not in checked
    assert "由双方协商并书面确认" in checked
    assert "合同效力结论" in checked


def test_contract_agent_applies_guard_to_run_and_stream():
    contract = "结算周期为活动结束后30个工作日内完成。"
    output = """## 重点风险清单

| 风险等级 | 规则编号与类别 | 原文证据 | AI 判断 | 修改建议 | 待确认信息 |
|---|---|---|---|---|---|
| 高 | CR-PAYMENT | 30个工作日 | AI 推断 | 增加5个工作日通知期，并设20%责任上限。 | 待确认 |
"""

    run_llm = FakeContractLLM(output)
    run_result = ContractAgent(run_llm).run(contract)
    assert "合同建议边界" in run_llm.prompts[0]
    assert "规则库关注级别" in run_llm.prompts[0]
    assert "5个工作日" not in run_result.content
    assert "20%" not in run_result.content
    assert "## 本地规则预检明细" in run_result.content
    assert run_result.mode == "AI模型模式（含本地规则预检）"

    stream_llm = FakeContractLLM(output)
    streamed = "".join(ContractAgent(stream_llm).stream(contract))
    assert "5个工作日" not in streamed
    assert "20%" not in streamed
    assert "## 自动一致性校验" in streamed
    assert "## 本地规则预检明细" in streamed
