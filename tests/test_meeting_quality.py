# -*- coding: utf-8 -*-
from __future__ import annotations

from zhilian_tianhe_agent.agents import MeetingAgent
from zhilian_tianhe_agent.meeting_quality import (
    MEETING_FACT_SAFETY_RULES,
    audit_meeting_output,
    build_meeting_evidence_v2,
)


MEETING_TEXT = """会议主题：天河路商圈暑期青年品牌联动促消费活动筹备会

会议时间：2026年7月8日 15:00-16:30
参会人员：商圈运营负责人李经理、市场推广负责人陈璐、法务顾问周律师、商户代表王先生、咖啡品牌负责人林女士、文创店负责人何女士、技术支持负责人赵工。

会议内容：
1. 本次活动暂定名称为“夏日有礼·智惠天河青年消费季”，计划联合30家商户开展满减优惠、打卡集章、短视频传播和会员积分活动。
2. 活动时间初步定为2026年8月1日至8月31日，7月15日前完成商户报名，7月20日前确认活动方案，7月25日前完成宣传物料设计。
3. 市场推广负责人陈璐负责制定统一宣传方案，包括小红书、抖音、公众号推文、商场电子屏海报和线下展架。
4. 商户代表王先生提出，希望明确各商户的费用承担比例、宣传资源权益、优惠券核销方式和客户数据使用边界。
5. 法务顾问周律师提醒，商户合作协议中需要明确活动费用、结算周期、违约责任、知识产权归属、顾客投诉处理和数据使用授权。
6. 技术支持负责人赵工建议引入AI工具，用于整理会议纪要、生成活动执行任务表、检查合作协议风险、生成商户对接话术，并形成每周进展报告。
7. 初步决定由运营组负责总协调，市场组负责宣传，法务顾问负责协议审阅，技术组负责AI工具配置，各商户需在7月15日前提交参与活动的优惠方案。
8. 下一次会议定于7月16日下午召开，重点确认商户名单、活动预算、宣传计划和合同模板。
"""


class FakeLlm:
    def chat(self, system_prompt: str, prompt: str) -> str:
        return _bad_model_output()

    def chat_stream(self, system_prompt: str, prompt: str):
        text = _bad_model_output()
        yield text[: len(text) // 2]
        yield text[len(text) // 2 :]


def _bad_model_output() -> str:
    return """## 一句话结论
需在7月15日前推进商户报名。[MT-05]

## 原文待办事项
| 事项 | 负责人 | 截止时间 | 证据编号 | 确认状态 | 优先级（AI 推断） | 依赖条件 | 待确认信息 |
|---|---|---|---|---|---|---|---|
| 启动商户报名通道 | 李经理（运营组） | 2026-07-12（建议） | [MT-05][MT-10] | 原文事实 | 高 | 待确认 | 待确认 |
| 各商户提交优惠方案 | 各商户 | 7月15日前 | [MT-10]（第7条） | 原文事实 | 高 | 待确认 | — |

## 风险提醒
| 风险类型 | 证据编号 | 风险说明（AI 推断） | 建议动作 | 待确认信息 |
|---|---|---|---|---|
| 结算风险 | [MT-07] | 尚未明确核销规则 | 设定T+3日对账、T+7日结算，并设置20元最低门槛 | 具体规则待确认 |
"""


def test_meeting_evidence_covers_all_numbered_items_without_generic_heading() -> None:
    bundle = build_meeting_evidence_v2(MEETING_TEXT, "使用身份：企业用户")
    meeting_items = [item for item in bundle.evidence if item.evidence_id.startswith("MT-")]

    assert len(meeting_items) == 11
    assert all(item.excerpt not in {"会议内容", "会议内容：", "会议内容:"} for item in meeting_items)
    assert meeting_items[8].evidence_id == "MT-09"
    assert "赵工建议引入AI工具" in meeting_items[8].excerpt
    assert meeting_items[9].evidence_id == "MT-10"
    assert "运营组负责总协调" in meeting_items[9].excerpt
    assert meeting_items[10].evidence_id == "MT-11"
    assert "下一次会议定于7月16日下午召开" in meeting_items[10].excerpt


def test_meeting_prompt_adds_strict_fact_boundary_rules() -> None:
    prompt, bundle = MeetingAgent(FakeLlm())._prepare(MEETING_TEXT, "使用身份：企业用户")

    assert MEETING_FACT_SAFETY_RULES in prompt
    assert "不得把团队责任推定为具体个人责任" in prompt
    assert "AI 建议补充动作" in prompt
    assert any(item.evidence_id == "MT-11" for item in bundle.evidence)


def test_audit_downgrades_unsupported_owner_deadline_and_hard_values() -> None:
    bundle = build_meeting_evidence_v2(MEETING_TEXT, "")
    checked = audit_meeting_output(_bad_model_output(), MEETING_TEXT, bundle)

    assert "[MT-10]（第7条）" not in checked
    assert "待确认（AI 建议：李经理（运营组））" in checked
    assert "待确认（AI 建议：2026-07-12（建议））" in checked
    assert "AI 建议（未确认）" in checked
    assert "T+3" not in checked
    assert "T+7" not in checked
    assert "20元" not in checked
    assert "具体周期、金额、阈值及审批方式待确认" in checked
    assert "自动一致性校验" in checked


def test_audit_preserves_explicit_group_owner_and_deadline() -> None:
    bundle = build_meeting_evidence_v2(MEETING_TEXT, "")
    checked = audit_meeting_output(_bad_model_output(), MEETING_TEXT, bundle)

    preserved_row = next(line for line in checked.splitlines() if "各商户提交优惠方案" in line)
    assert "| 各商户 | 7月15日前 | [MT-10] | 原文事实 |" in preserved_row


def test_stream_buffers_and_audits_before_returning_result() -> None:
    output = "".join(MeetingAgent(FakeLlm()).stream(MEETING_TEXT))

    assert "T+3" not in output
    assert "AI 建议（未确认）" in output
    assert "## 输入证据与待确认索引" in output
    assert "MT-11" in output
