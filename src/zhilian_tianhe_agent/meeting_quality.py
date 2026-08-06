# -*- coding: utf-8 -*-
"""Deterministic meeting evidence and output fact-boundary checks."""
from __future__ import annotations

import re
from typing import Iterable

from .evidence import EvidenceBundle, EvidenceItem, PendingConfirmation

MAX_MEETING_EVIDENCE = 11
MAX_EXCERPT_CHARS = 360

MEETING_FACT_SAFETY_RULES = """
【会议事实边界：最高优先级】
1. 证据引用只能使用服务端证据索引中完整存在的编号，格式仅为 `[MT-01]` 或 `[MP-01]`。禁止写 `[MT-07]（第6条）`、`[MT-07]（末句）` 等伪定位，也不得让一个证据编号代表其他段落。
2. “原文事实”或“已明确”必须得到对应证据逐字段支持。待办事项的任务、负责人、截止时间只要有一项不是原文明确内容，就必须把该项写为“待确认”，确认状态写“部分明确”或“AI 建议（未确认）”。
3. 不得把团队责任推定为具体个人责任。例如“运营组负责”不能改写成“李经理负责”；只有原文明确出现“某人负责某事”时才可填写该人。
4. 不得创造原文没有的日期、周期、金额、比例、阈值、数量、审批人数或服务承诺。禁止自行增加如 7 月 12 日、7 月 14 日、T+3、T+7、20 元、1.5 倍、双签、四步流程等具体值。
5. 主表“待办事项表”只收录原文已经提出的动作。模型补充的动作必须放入独立的“AI 建议补充动作”章节，并统一标记“AI 建议（未确认）”，负责人、截止时间默认写“待确认”。
6. “暂定、初步决定、建议、希望、提出、提醒”不等于最终批准。暂定名称、初步时间和讨论意见应标记“拟议/待确认”。
7. 风险说明可以是 AI 推断，但建议动作不得包含原文没有的具体结算周期、金额门槛、转化目标、数据保存期限或审批机制；需要数值时写“具体数值待确认”。
8. 一句话结论只能引用直接支持该结论的证据，不得堆叠无关编号。

必须按以下顺序输出：一句话结论、会议摘要、关键决策、原文待办事项、AI 建议补充动作、风险提醒、待确认信息、下次会议议题。
""".strip()


def build_meeting_evidence_v2(
    meeting_text: str,
    profile_summary: str = "",
) -> EvidenceBundle:
    """Build evidence for all meaningful meeting lines, reserving one profile slot."""
    segments = _meeting_segments(meeting_text)
    evidence: list[EvidenceItem] = [
        EvidenceItem(
            evidence_id=f"MT-{index:02d}",
            source_type="用户输入",
            source="会议原文",
            field="会议记录",
            excerpt=_trim(segment),
        )
        for index, segment in enumerate(segments[:MAX_MEETING_EVIDENCE], start=1)
    ]
    summary = _space(profile_summary)
    if summary and len(evidence) < 12:
        evidence.append(
            EvidenceItem(
                evidence_id="MP-01",
                source_type="上下文输入",
                source="企业档案摘要",
                field="企业背景",
                excerpt=_trim(summary),
            )
        )

    pending: list[PendingConfirmation] = []
    normalized = _space(meeting_text)
    if not re.search(r"\d{4}[年/-]\d{1,2}|今天|明天|本周|下周|截止|之前|以内", normalized):
        pending.append(PendingConfirmation("MT-C01", "请确认待办事项的具体截止时间。"))
    if not re.search(r"负责|负责人|牵头|跟进|对接|由.{0,16}(负责|完成)", normalized):
        pending.append(PendingConfirmation("MT-C02", "请确认每项待办的负责人或牵头角色。"))
    if not re.search(r"决定|确认|通过|同意|结论|初步决定|暂定", normalized):
        pending.append(PendingConfirmation("MT-C03", "请确认哪些内容属于已确定决策，哪些仍是讨论意见。"))
    if re.search(r"预算|费用|分摊|结算", normalized) and not re.search(r"\d+(?:\.\d+)?\s*(?:元|万元|%|％)", normalized):
        pending.append(PendingConfirmation("MT-C04", "会议提到预算、费用或结算，但未明确具体金额、比例或规则。"))
    if re.search(r"数据|客户信息|个人信息|授权", normalized):
        pending.append(PendingConfirmation("MT-C05", "请确认数据范围、授权方式、使用目的、保存期限和责任边界。"))
    if re.search(r"暂定|初步决定|建议|希望|提出", normalized):
        pending.append(PendingConfirmation("MT-C06", "请确认暂定方案和讨论意见中哪些已经获得最终批准。"))

    return EvidenceBundle(
        module="会议纪要",
        evidence=tuple(evidence),
        pending_confirmations=tuple(_unique_confirmations(pending)),
        limitations=(
            "证据编号逐条对应会议原文，不允许用一个编号代指其他条目。只有原文明确出现的任务、负责人、"
            "日期和数量才能标记为事实；模型补充内容必须标记为 AI 建议并由业务人员确认。"
        ),
    )


def audit_meeting_output(
    content: str,
    meeting_text: str,
    bundle: EvidenceBundle,
) -> str:
    """Conservatively downgrade unsupported meeting assignments and hard values."""
    valid_ids = {item.evidence_id for item in bundle.evidence}
    evidence_by_id = {item.evidence_id: item.excerpt for item in bundle.evidence}
    source_text = _space(meeting_text)
    corrections = 0

    # Remove misleading pseudo-locations such as [MT-07]（第6条）.
    cleaned, count = re.subn(r"(\[(?:MT|MP)-\d{2}\])\s*[（(](?:第[^）)]*条|末句|隐含[^）)]*)[）)]", r"\1", content)
    corrections += count

    def replace_invalid_reference(match: re.Match[str]) -> str:
        nonlocal corrections
        evidence_id = match.group(1)
        if evidence_id in valid_ids:
            return match.group(0)
        corrections += 1
        return "[证据编号待核对]"

    cleaned = re.sub(r"\[((?:MT|MP)-\d{2})\]", replace_invalid_reference, cleaned)

    lines = cleaned.splitlines()
    output: list[str] = []
    section = ""
    headers: list[str] | None = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            section = stripped[3:].strip()
            headers = None
            output.append(line)
            continue
        if not _is_table_row(stripped):
            if stripped:
                headers = None
            output.append(line)
            continue

        cells = _split_table_row(stripped)
        if headers is None:
            headers = cells
            output.append(line)
            continue
        if _is_separator_row(cells):
            output.append(line)
            continue

        if section in {"待办事项表", "原文待办事项"}:
            cells, changed = _audit_task_row(cells, headers, evidence_by_id)
            corrections += changed
        elif section == "风险提醒":
            cells, changed = _audit_risk_row(cells, headers, evidence_by_id, source_text)
            corrections += changed
        output.append(_join_table_row(cells))

    result = "\n".join(output).strip()
    if corrections:
        result += (
            "\n\n## 自动一致性校验\n\n"
            f"> 系统已对 {corrections} 处证据引用、负责人、截止时间或具体数值进行保守校正。"
            "未获会议原文直接支持的内容已降级为“AI 建议（未确认）”或“待确认”。"
        )
    return result


def _audit_task_row(
    cells: list[str],
    headers: list[str],
    evidence_by_id: dict[str, str],
) -> tuple[list[str], int]:
    changed = 0
    owner_index = _header_index(headers, "负责人")
    deadline_index = _header_index(headers, "截止时间")
    status_index = _header_index(headers, "确认状态", "状态")
    evidence_index = _header_index(headers, "证据编号", "原文证据")
    cited = _cited_excerpts(cells[evidence_index] if evidence_index is not None and evidence_index < len(cells) else "", evidence_by_id)
    unsupported = False

    if owner_index is not None and owner_index < len(cells):
        owner = cells[owner_index].strip()
        if owner and "待确认" not in owner and not _owner_supported(owner, cited):
            cells[owner_index] = f"待确认（AI 建议：{owner}）"
            changed += 1
            unsupported = True

    if deadline_index is not None and deadline_index < len(cells):
        deadline = cells[deadline_index].strip()
        if deadline and "待确认" not in deadline and not _deadline_supported(deadline, cited):
            cells[deadline_index] = f"待确认（AI 建议：{deadline}）"
            changed += 1
            unsupported = True

    if status_index is not None and status_index < len(cells):
        status = cells[status_index].strip()
        if unsupported and status in {"原文事实", "已明确", "明确"}:
            cells[status_index] = "AI 建议（未确认）"
            changed += 1
        elif "建议" in " ".join(cells) and status == "原文事实":
            cells[status_index] = "AI 建议（未确认）"
            changed += 1
    return cells, changed


def _audit_risk_row(
    cells: list[str],
    headers: list[str],
    evidence_by_id: dict[str, str],
    source_text: str,
) -> tuple[list[str], int]:
    action_index = _header_index(headers, "建议动作")
    evidence_index = _header_index(headers, "证据编号")
    if action_index is None or action_index >= len(cells):
        return cells, 0
    action = cells[action_index]
    cited = " ".join(_cited_excerpts(cells[evidence_index] if evidence_index is not None and evidence_index < len(cells) else "", evidence_by_id))
    support_text = _space(cited + " " + source_text)
    hard_values = _hard_value_tokens(action)
    if hard_values and any(token not in support_text for token in hard_values):
        cells[action_index] = "建议先明确规则和责任边界；具体周期、金额、阈值及审批方式待确认。"
        return cells, 1
    if any(term in action for term in ("双签", "四步流程", "强制使用")) and not any(term in support_text for term in ("双签", "四步流程", "强制使用")):
        cells[action_index] = "建议先明确规则和责任边界；具体流程及审批方式待确认。"
        return cells, 1
    return cells, 0


def _meeting_segments(value: str) -> list[str]:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"(^|\n)\s*会议内容\s*[：:]\s*", "\n", text)
    # Keep numbered agenda items independent even when pasted into one paragraph.
    text = re.sub(r"(?<!\d)(?=(?:[1-9]|1\d)[.、]\s*)", "\n", text)
    raw_lines = [_space(line) for line in text.split("\n")]
    segments: list[str] = []
    for line in raw_lines:
        if not line or line in {"会议内容", "会议内容：", "会议内容:"}:
            continue
        if len(line) > 700 and not re.match(r"^(?:[1-9]|1\d)[.、]", line):
            parts = re.split(r"(?<=[。！？；])", line)
        else:
            parts = [line]
        for part in parts:
            normalized = _space(part)
            if normalized and normalized not in segments:
                segments.append(normalized)
    return segments


def _cited_excerpts(value: str, evidence_by_id: dict[str, str]) -> list[str]:
    ids = re.findall(r"\[((?:MT|MP)-\d{2})\]", value or "")
    return [evidence_by_id[item] for item in ids if item in evidence_by_id]


def _owner_supported(owner: str, excerpts: Iterable[str]) -> bool:
    tokens = [
        token
        for token in re.findall(r"[\u4e00-\u9fff]{2,}", re.sub(r"[（(][^）)]*[）)]", " ", owner))
        if token not in {"负责人", "待确认", "建议", "原文", "相关人员"}
    ]
    parenthetical = re.findall(r"[（(]([^）)]*)[）)]", owner)
    for item in parenthetical:
        tokens.extend(token for token in re.findall(r"[\u4e00-\u9fff]{2,}", item) if token)
    tokens = list(dict.fromkeys(tokens))
    if not tokens:
        return False
    for excerpt in excerpts:
        normalized = _space(excerpt)
        if all(token in normalized for token in tokens) and re.search(r"负责|牵头|跟进|对接|需在|由.{0,16}完成", normalized):
            return True
    return False


def _deadline_supported(deadline: str, excerpts: Iterable[str]) -> bool:
    tokens = _date_tokens(deadline)
    if not tokens:
        return False
    for excerpt in excerpts:
        excerpt_tokens = set(_date_tokens(excerpt))
        if all(token in excerpt_tokens for token in tokens):
            return True
    return False


def _date_tokens(value: str) -> list[str]:
    text = _space(value)
    result: list[str] = []
    for year, month, day in re.findall(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})日?", text):
        result.append(f"{int(year):04d}-{int(month):02d}-{int(day):02d}")
    for month, day in re.findall(r"(?<!\d)(\d{1,2})月(\d{1,2})日?", text):
        token = f"{int(month):02d}-{int(day):02d}"
        if not any(item.endswith(token) for item in result):
            result.append(token)
    return list(dict.fromkeys(result))


def _hard_value_tokens(value: str) -> list[str]:
    patterns = (
        r"T\+\d+",
        r"\d+(?:\.\d+)?\s*(?:元|万元|%|％|倍|x|X)",
        r"\d+(?:\.\d+)?\s*(?:天|日|小时|分钟)",
    )
    result: list[str] = []
    for pattern in patterns:
        result.extend(_space(item) for item in re.findall(pattern, value or ""))
    return list(dict.fromkeys(result))


def _header_index(headers: list[str], *names: str) -> int | None:
    for index, header in enumerate(headers):
        if any(name in header for name in names):
            return index
    return None


def _is_table_row(line: str) -> bool:
    return line.startswith("|") and line.endswith("|") and line.count("|") >= 2


def _split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _join_table_row(cells: list[str]) -> str:
    return "| " + " | ".join(cell.replace("|", "｜") for cell in cells) + " |"


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)


def _trim(value: object) -> str:
    text = _space(value)
    return text if len(text) <= MAX_EXCERPT_CHARS else text[: MAX_EXCERPT_CHARS - 1].rstrip() + "…"


def _space(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _unique_confirmations(values: Iterable[PendingConfirmation]) -> list[PendingConfirmation]:
    result: list[PendingConfirmation] = []
    seen: set[str] = set()
    for value in values:
        if value.question not in seen:
            seen.add(value.question)
            result.append(value)
    return result
