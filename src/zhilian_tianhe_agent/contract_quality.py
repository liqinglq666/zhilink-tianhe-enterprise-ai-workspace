# -*- coding: utf-8 -*-
"""Contract recommendation boundaries and deterministic output checks."""
from __future__ import annotations

import re

from .contract_rules import ContractRuleScan


CONTRACT_RECOMMENDATION_SAFETY_RULES = """
【合同建议边界：最高优先级】
1. 必须区分三层信息：合同原文、本地规则预检、AI 商务建议。本地规则命中只说明关键词风险方向，不是法律结论；AI 建议不是双方已同意条款。
2. “原文证据”必须逐字来自合同文本，不得把解释、行业惯例或建议条款混入原文证据。
3. 合同原文没有给出的期限、金额、比例、次数、阈值、地域、保存周期、通知期、整改期和责任上限，不得自行生成具体数字。需要表达时写“具体数值由双方协商并书面确认”。
4. 禁止把示例值包装成标准答案，例如“5 个工作日通知、3 日整改、20% 责任上限、最长顺延 15 日、额外成本 500 元、保存 6 个月”等。
5. 修改建议只能写“修改方向（AI 建议）”，不得使用“须、必须、应当采用某数值”等确定性措辞。可以建议明确计算方式、触发条件、上限、通知流程和责任边界，但具体参数应留待双方协商。
6. 不得凭空限定数据字段、授权地域、使用年度、整改次数、验收轮次或争议解决地点。合同未提供的信息必须进入“待确认信息”。
7. 可以建议明确是否允许模型训练、营销或第三方共享，但不得把禁止或允许写成已经适用于双方的既定规则。
8. 风险等级应同时展示“本地规则等级”和“AI 综合判断”，不得把关键词命中描述为法律违法或合同必然无效。
9. 签约前检查清单只写需要确认的问题，不得在问题中预填未经原文支持的期限、比例、金额或流程答案。
10. 本报告只做商务风险识别和修改方向提示，不替代律师对完整合同、附件、交易背景和适用法律的审阅。
""".strip()


_TARGET_SECTIONS = {"重点风险清单", "建议补充条款", "签约前检查清单"}

_HARD_VALUE_PATTERN = re.compile(
    r"(?:T\s*\+\s*\d+)|"
    r"(?:\d{4}\s*年度)|"
    r"(?:\d{4}[年/-]\d{1,2}(?:[月/-]\d{1,2}日?)?)|"
    r"(?:\d+(?:\.\d+)?\s*(?:%|％|倍))|"
    r"(?:\d+(?:\.\d+)?\s*(?:元|万元|亿元))|"
    r"(?:\d+(?:\.\d+)?\s*(?:个)?(?:工作日|日|天|周|个月|月|年|小时|次|轮))",
    re.IGNORECASE,
)

_FIXED_SCOPE_PATTERNS = (
    re.compile(r"仅限[^；。|]{1,100}(?:[一二三四五六七八九十\d]+项)"),
    re.compile(r"(?:双签|双人审批|两人审批|三方审批)"),
)


def audit_contract_output(
    content: str,
    contract_text: str,
    scan: ContractRuleScan,
) -> str:
    """Downgrade unsupported numeric clause prescriptions to negotiation variables.

    The audit only changes recommendation-oriented sections. Source quotes, rule
    evidence and deterministic scan counts are left untouched.
    """
    source_values = {_canonical_value(item) for item in _HARD_VALUE_PATTERN.findall(contract_text or "")}
    corrections = 0
    section = ""
    headers: list[str] | None = None
    output: list[str] = []

    for line in (content or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            section = stripped[3:].strip()
            headers = None
            output.append(line)
            continue

        if section == "重点风险清单" and _is_table_row(stripped):
            cells = _split_table_row(stripped)
            if headers is None:
                headers = cells
                output.append(line)
                continue
            if _is_separator_row(cells):
                output.append(line)
                continue
            suggestion_index = _header_index(headers, "修改建议", "修改方向", "修改方向（AI 建议）")
            if suggestion_index is not None and suggestion_index < len(cells):
                cells[suggestion_index], changed = _sanitize_recommendation(
                    cells[suggestion_index], source_values
                )
                corrections += changed
            output.append(_join_table_row(cells))
            continue

        if section in {"建议补充条款", "签约前检查清单"} and stripped:
            sanitized, changed = _sanitize_recommendation(line, source_values)
            corrections += changed
            output.append(sanitized)
            continue

        if stripped:
            headers = None
        output.append(line)

    result = "\n".join(output).strip()
    if corrections:
        result += (
            "\n\n## 自动一致性校验\n\n"
            f"> 系统已对 {corrections} 处未经合同原文支持的期限、金额、比例、阈值或固定流程进行保守校正。"
            "这些内容已改为待双方协商确认的 AI 建议，不代表法律标准或双方已达成条款。"
        )
    return result


def _sanitize_recommendation(text: str, source_values: set[str]) -> tuple[str, int]:
    corrections = 0

    def replace_value(match: re.Match[str]) -> str:
        nonlocal corrections
        raw = match.group(0)
        if _canonical_value(raw) in source_values:
            return raw
        corrections += 1
        return "【具体数值待双方协商】"

    sanitized = _HARD_VALUE_PATTERN.sub(replace_value, text)

    for pattern in _FIXED_SCOPE_PATTERNS:
        sanitized, count = pattern.subn("具体范围和审批机制由双方书面确认", sanitized)
        corrections += count

    # Remove repeated placeholders produced by adjacent hard values.
    sanitized = re.sub(
        r"(?:【具体数值待双方协商】\s*[、，和及或至~-]?\s*){2,}",
        "【具体数值待双方协商】",
        sanitized,
    )
    return sanitized, corrections


def _canonical_value(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "")).casefold()


def _is_table_row(line: str) -> bool:
    return line.startswith("|") and line.endswith("|") and line.count("|") >= 3


def _split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _join_table_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)


def _header_index(headers: list[str], *names: str) -> int | None:
    for index, header in enumerate(headers):
        normalized = re.sub(r"\s+", "", header)
        if any(re.sub(r"\s+", "", name) in normalized for name in names):
            return index
    return None
