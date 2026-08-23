# -*- coding: utf-8 -*-
"""Deterministic evidence indexes and pending-confirmation bundles."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

MAX_EVIDENCE_ITEMS = 12
MAX_EXCERPT_CHARS = 240


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    source_type: str
    source: str
    field: str
    excerpt: str

    def to_prompt_dict(self) -> dict[str, str]:
        return {
            "evidence_id": self.evidence_id,
            "source_type": self.source_type,
            "source": self.source,
            "field": self.field,
            "excerpt": self.excerpt,
        }


@dataclass(frozen=True)
class PendingConfirmation:
    confirmation_id: str
    question: str

    def to_prompt_dict(self) -> dict[str, str]:
        return {
            "confirmation_id": self.confirmation_id,
            "question": self.question,
        }


@dataclass(frozen=True)
class EvidenceBundle:
    module: str
    evidence: tuple[EvidenceItem, ...]
    pending_confirmations: tuple[PendingConfirmation, ...]
    limitations: str

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "bundle_type": "deterministic_input_evidence_index",
            "module": self.module,
            "limitations": self.limitations,
            "evidence": [item.to_prompt_dict() for item in self.evidence],
            "pending_confirmations": [
                item.to_prompt_dict() for item in self.pending_confirmations
            ],
        }

    def to_markdown(self) -> str:
        lines = [
            "## 输入证据与待确认索引",
            "",
            f"> {self.limitations}",
            "",
        ]
        if self.evidence:
            lines.extend(
                [
                    "| 证据编号 | 类型 | 来源 | 字段 | 输入摘录 |",
                    "|---|---|---|---|---|",
                ]
            )
            for item in self.evidence:
                lines.append(
                    "| {evidence_id} | {source_type} | {source} | {field} | {excerpt} |".format(
                        evidence_id=_escape_table_cell(item.evidence_id),
                        source_type=_escape_table_cell(item.source_type),
                        source=_escape_table_cell(item.source),
                        field=_escape_table_cell(item.field),
                        excerpt=_escape_table_cell(item.excerpt),
                    )
                )
        else:
            lines.append("- 没有可建立索引的非空输入；本次结果不应形成确定性业务结论。")

        lines.extend(["", "### 待确认信息", ""])
        if self.pending_confirmations:
            for item in self.pending_confirmations:
                lines.append(f"- [ ] [{item.confirmation_id}] {item.question}")
        else:
            lines.append("- [ ] 暂无系统自动识别的缺口，仍需业务人员复核全部关键事实。")
        return "\n".join(lines).strip()


def append_evidence_appendix(content: str, bundle: EvidenceBundle) -> str:
    return f"{content.rstrip()}\n\n{bundle.to_markdown()}".strip()


def build_profile_evidence(profile: Mapping[str, Any]) -> EvidenceBundle:
    field_labels = {
        "name": "企业名称",
        "industry": "行业方向",
        "location": "所在区域或场景",
        "scale": "团队或经营规模",
        "stage": "发展阶段",
        "contact_role": "联系人角色",
        "demands": "当前需求",
    }
    evidence = _mapping_evidence("PF", "用户输入", "企业档案表单", profile, field_labels)
    pending = _pending_for_missing(
        "PF",
        profile,
        {
            "name": "请确认企业或经营主体的正式名称。",
            "industry": "请确认企业所属行业及主营业务。",
            "stage": "请确认当前发展阶段，避免优先级判断失真。",
            "demands": "请确认本次最需要解决的具体业务问题。",
        },
    )
    return _bundle("企业档案", evidence, pending)


def build_meeting_evidence(
    meeting_text: str,
    profile_summary: str = "",
) -> EvidenceBundle:
    evidence = list(
        _text_evidence("MT", "用户输入", "会议原文", "会议记录", meeting_text, 8)
    )
    evidence.extend(
        _text_evidence(
            "MP",
            "上下文输入",
            "企业档案摘要",
            "企业背景",
            profile_summary,
            3,
        )
    )
    pending: list[PendingConfirmation] = []
    normalized = _normalize(meeting_text)
    if not re.search(r"\d{4}[年/-]\d{1,2}|今天|明天|本周|下周|截止|之前|以内", normalized):
        pending.append(PendingConfirmation("MT-C01", "请确认待办事项的具体截止时间。"))
    if not re.search(r"负责|负责人|牵头|跟进|对接|由.{0,12}(负责|完成)", normalized):
        pending.append(PendingConfirmation("MT-C02", "请确认每项待办的负责人或牵头角色。"))
    if not re.search(r"决定|确认|通过|同意|结论|初步决定", normalized):
        pending.append(PendingConfirmation("MT-C03", "请确认哪些内容属于已确定决策，哪些仍是讨论意见。"))
    return _bundle("会议纪要", evidence, pending)


def build_policy_evidence(
    profile: Mapping[str, Any],
    demand: str,
    policy_directions: Iterable[Mapping[str, Any]],
) -> EvidenceBundle:
    evidence = list(
        _mapping_evidence(
            "PL",
            "用户输入",
            "企业档案表单",
            profile,
            {
                "name": "企业名称",
                "industry": "行业方向",
                "location": "所在区域或场景",
                "scale": "规模",
                "stage": "发展阶段",
                "demands": "企业需求",
            },
            max_items=7,
        )
    )
    evidence.extend(_text_evidence("PD", "用户输入", "政策需求", "需求描述", demand, 3))
    direction_names: list[str] = []
    for direction in policy_directions:
        if isinstance(direction, Mapping):
            name = str(
                direction.get("name")
                or direction.get("direction")
                or direction.get("title")
                or ""
            ).strip()
            if name:
                direction_names.append(name)
    if direction_names:
        evidence.append(
            EvidenceItem(
                evidence_id="PR-01",
                source_type="本地参考",
                source="政策方向库",
                field="方向名称",
                excerpt=_trim("、".join(direction_names)),
            )
        )
    pending = _pending_for_missing(
        "PL",
        profile,
        {
            "industry": "请确认主营行业和业务范围，以便判断政策方向适配性。",
            "location": "请确认注册地、经营地或项目实施地。",
            "scale": "请确认企业规模、营收或人员等申报相关基础信息。",
            "stage": "请确认项目当前阶段和计划实施时间。",
        },
    )
    if not _normalize(demand):
        pending.append(PendingConfirmation("PD-C01", "请确认本次希望了解的政策主题或准备目标。"))
    pending.append(
        PendingConfirmation(
            "PR-C01",
            "当前仅使用本地政策方向库，正式申报前必须核对真实政策名称、发布部门、发布日期、有效期和官方原文。",
        )
    )
    return _bundle(
        "政策准备",
        evidence,
        pending,
        limitations=(
            "本索引区分用户输入和本地方向库参考；本地方向库不是实时政策检索结果，"
            "不能作为政策名称、有效性或申报资格的官方依据。"
        ),
    )


def build_match_evidence(
    profile: Mapping[str, Any],
    offer: str,
    need: str,
    target: str,
    scenario: str,
) -> EvidenceBundle:
    evidence = list(
        _mapping_evidence(
            "MF",
            "上下文输入",
            "企业档案",
            profile,
            {
                "name": "企业名称",
                "industry": "行业",
                "location": "区域或场景",
                "demands": "企业需求",
            },
            max_items=4,
        )
    )
    for prefix, field, value in (
        ("MO", "我能提供", offer),
        ("MN", "我需要", need),
        ("MT", "希望对接对象", target),
        ("MS", "业务场景", scenario),
    ):
        evidence.extend(_text_evidence(prefix, "用户输入", "供需协作表单", field, value, 2))
    pending: list[PendingConfirmation] = []
    for confirmation_id, value, question in (
        ("MO-C01", offer, "请确认可提供资源的数量、范围、使用条件和有效期。"),
        ("MN-C01", need, "请确认需求优先级、预算范围和期望完成时间。"),
        ("MT-C01", target, "请确认希望对接的具体对象类型和准入条件。"),
        ("MS-C01", scenario, "请确认合作发生的具体场景、地点和试点范围。"),
    ):
        if not _normalize(value):
            pending.append(PendingConfirmation(confirmation_id, question))
    return _bundle("供需协作", evidence, pending)


def build_landing_evidence(
    profile: Mapping[str, Any],
    landing_info: Mapping[str, Any],
    existing_results: Mapping[str, Any],
) -> EvidenceBundle:
    evidence = list(
        _mapping_evidence(
            "LF",
            "上下文输入",
            "企业档案",
            profile,
            {
                "name": "企业名称",
                "industry": "行业",
                "location": "区域或场景",
                "demands": "企业需求",
            },
            max_items=4,
        )
    )
    evidence.extend(
        _mapping_evidence(
            "LC",
            "用户输入",
            "落地配置",
            landing_info,
            {
                "pilot_scene": "试点场景",
                "user_roles": "使用角色",
                "data_scope": "数据范围",
                "deployment": "部署方式",
                "pilot_period": "试点周期",
                "review_mode": "复核机制",
            },
            max_items=6,
        )
    )
    evidence.extend(
        _mapping_evidence(
            "LR",
            "既有结果",
            "已生成模块",
            existing_results,
            {},
            max_items=6,
        )
    )
    pending = _pending_for_missing(
        "LC",
        landing_info,
        {
            "pilot_scene": "请确认首个试点场景和明确的业务边界。",
            "user_roles": "请确认实际使用人员、负责人和复核人员。",
            "data_scope": "请确认允许处理的数据范围及禁止输入的信息。",
            "pilot_period": "请确认试点开始时间、周期和结束条件。",
            "review_mode": "请确认人工复核、批准和异常升级机制。",
        },
    )
    if not any(_normalize(value) for value in existing_results.values()):
        pending.append(PendingConfirmation("LR-C01", "当前没有可引用的既有模块结果，请确认实施计划所依据的业务材料。"))
    return _bundle("实施计划", evidence, pending)


def build_report_evidence(all_results: Mapping[str, Any]) -> EvidenceBundle:
    evidence = _mapping_evidence(
        "RP",
        "既有结果",
        "模块生成结果",
        all_results,
        {},
        max_items=MAX_EVIDENCE_ITEMS,
    )
    pending: list[PendingConfirmation] = []
    missing = [str(key) for key, value in all_results.items() if not _normalize(value)]
    if missing:
        pending.append(
            PendingConfirmation(
                "RP-C01",
                f"以下模块没有可引用结果，请确认是否应补充后再归档：{'、'.join(missing)}。",
            )
        )
    pending.append(
        PendingConfirmation(
            "RP-C02",
            "请由业务负责人确认综合报告没有把模块建议误写成已发生事实或已批准决定。",
        )
    )
    return _bundle("综合报告", evidence, pending)


def _bundle(
    module: str,
    evidence: Iterable[EvidenceItem],
    pending: Iterable[PendingConfirmation],
    *,
    limitations: str | None = None,
) -> EvidenceBundle:
    return EvidenceBundle(
        module=module,
        evidence=tuple(list(evidence)[:MAX_EVIDENCE_ITEMS]),
        pending_confirmations=tuple(_unique_confirmations(pending)),
        limitations=limitations
        or (
            "本节由服务端根据用户输入和既有结果确定性生成。证据摘录只证明输入中出现过相关表述；"
            "所有解释、优先级、建议和预测均属于 AI 推断，必须由业务人员确认。"
        ),
    )


def _mapping_evidence(
    prefix: str,
    source_type: str,
    source: str,
    values: Mapping[str, Any],
    field_labels: Mapping[str, str],
    *,
    max_items: int = MAX_EVIDENCE_ITEMS,
) -> list[EvidenceItem]:
    result: list[EvidenceItem] = []
    for key, value in values.items():
        text = _normalize(value)
        if not text:
            continue
        result.append(
            EvidenceItem(
                evidence_id=f"{prefix}-{len(result) + 1:02d}",
                source_type=source_type,
                source=source,
                field=field_labels.get(str(key), str(key)),
                excerpt=_trim(text),
            )
        )
        if len(result) >= max_items:
            break
    return result


def _text_evidence(
    prefix: str,
    source_type: str,
    source: str,
    field: str,
    value: str,
    max_items: int,
) -> list[EvidenceItem]:
    segments = _segments(value)
    return [
        EvidenceItem(
            evidence_id=f"{prefix}-{index:02d}",
            source_type=source_type,
            source=source,
            field=field,
            excerpt=_trim(segment),
        )
        for index, segment in enumerate(segments[:max_items], start=1)
    ]


def _pending_for_missing(
    prefix: str,
    values: Mapping[str, Any],
    questions: Mapping[str, str],
) -> list[PendingConfirmation]:
    result: list[PendingConfirmation] = []
    for index, (key, question) in enumerate(questions.items(), start=1):
        if not _normalize(values.get(key)):
            result.append(PendingConfirmation(f"{prefix}-C{index:02d}", question))
    return result


def _segments(value: str) -> list[str]:
    raw = re.split(r"(?<=[。！？；])|[\r\n]+", value or "")
    return _unique_text(_trim(item) for item in raw if _normalize(item))


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _trim(value: Any) -> str:
    text = _normalize(value)
    if len(text) <= MAX_EXCERPT_CHARS:
        return text
    return text[: MAX_EXCERPT_CHARS - 1].rstrip() + "…"


def _escape_table_cell(value: Any) -> str:
    return _normalize(value).replace("|", "｜")


def _unique_text(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _unique_confirmations(
    values: Iterable[PendingConfirmation],
) -> list[PendingConfirmation]:
    result: list[PendingConfirmation] = []
    seen: set[str] = set()
    for value in values:
        if value.question not in seen:
            seen.add(value.question)
            result.append(value)
    return result
