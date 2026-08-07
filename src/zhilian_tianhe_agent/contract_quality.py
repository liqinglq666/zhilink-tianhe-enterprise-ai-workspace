# -*- coding: utf-8 -*-
"""Contract recommendation boundaries and deterministic output checks."""
from __future__ import annotations

import re

from .contract_rules import ContractRuleScan


CONTRACT_RECOMMENDATION_SAFETY_RULES = """
【合同建议边界：最高优先级】
1. 必须区分三层信息：合同原文、本地规则预检、AI 商务建议。本地规则命中只说明关键词关注方向，不是法律结论；AI 建议不是双方已同意条款。
2. “原文证据”必须逐字来自合同文本，不得把解释、行业惯例或建议条款混入原文证据。
3. 合同原文没有给出的期限、金额、比例、次数、阈值、地域、保存周期、通知期、整改期和责任上限，不得自行生成具体数字。需要表达时写“具体数值由双方协商并书面确认”。
4. 禁止把示例值包装成标准答案，例如“5 个工作日通知、3 日整改、20% 责任上限、最长顺延 15 日、额外成本 500 元、保存 6 个月”等。
5. 修改建议只能写“修改方向（AI 建议）”，不得使用“须、必须、应当采用某数值”等确定性措辞。可以建议明确计算方式、触发条件、上限、通知流程和责任边界，但具体参数应留待双方协商。
6. 不得凭空限定数据字段、授权地域、使用年度、整改次数、验收轮次或争议解决地点。合同未提供的信息必须进入“待确认信息”。
7. 可以建议双方协商是否允许模型训练、营销或第三方共享，但不得把“禁止/允许”写成已经适用于双方的既定规则。
8. 本地规则中的“高/中/低”只能称为“规则库关注级别”或“高关注提示”，不得称为法律风险结论、违法结论或合同效力结论。
9. AI 可以给出综合关注等级，但必须明确为“AI 初步判断/AI 综合判断”，并提示需要人工复核。
10. 签约前检查清单只写需要确认的问题，不得在问题中预填未经原文支持的期限、比例、金额或流程答案。
11. 不得凭空赋予任何一方署名权、优先续约权、退出权、独占或非独占授权、固定地域授权等交易权利。只能提示双方协商相关安排并书面确认。
12. 本报告只做商务风险识别和修改方向提示，不替代律师对完整合同、附件、交易背景和适用法律的审阅。
""".strip()


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

_PRESCRIPTIVE_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"(?:明确)?禁止用于([^；。|]+)"),
        r"建议明确是否允许用于\1，并由双方协商后书面确认",
    ),
    (
        re.compile(r"不得用于([^；。|]+)"),
        r"建议明确是否允许用于\1，并由双方协商后书面确认",
    ),
    (
        re.compile(r"(?:仅授予|授予)[^；。|]{0,100}?(?:非独占性|独占性)(?:宣传)?使用权"),
        "建议明确既有标识或素材的授权场景、期限、地域、独占性及转授权边界",
    ),
    (
        re.compile(r"(?:乙方|甲方)享有署名权及同等条件下优先续约权"),
        "署名、续约及其他后续权益由双方协商并书面确认",
    ),
    (
        re.compile(r"(?:乙方|甲方)享有署名权"),
        "署名安排由双方协商并书面确认",
    ),
    (
        re.compile(r"(?:乙方|甲方)享有[^；。|]{0,30}优先续约权"),
        "续约及其他后续权益由双方协商并书面确认",
    ),
    (
        re.compile(r"(?:著作权|知识产权)归(?:甲方|乙方)所有"),
        "新成果的权利归属、使用许可和费用安排由双方协商并书面确认",
    ),
    (
        re.compile(r"(?:甲方|乙方)有权退出并[^；。|]+"),
        "退出条件及已发生费用的结算方式由双方协商并书面确认",
    ),
    (
        re.compile(r"逾期(?:未付|付款)[^；。|]{0,30}(?:计息|违约金)[^；。|]*"),
        "建议协商是否设置逾期利息或违约责任，并书面确认计算方式",
    ),
    (
        re.compile(r"单方调整权仅适用于[^；。|]+"),
        "建议明确单方调整权的触发情形、通知程序和补偿边界",
    ),
)

_OVERCLAIM_REPLACEMENTS = {
    "本地高风险命中数": "规则库高关注提示数",
    "本地命中类别数": "规则库关注类别数",
    "本地高风险命中": "规则库高关注提示",
    "本地规则判为高风险": "本地规则库提示为高关注项（非法律结论）",
    "本地高风险命中成立": "本地规则库提示为高关注项（非法律结论）",
    "本地中风险命中成立": "本地规则库提示为中度关注项（非法律结论）",
    "AI 升级为最高优先级风险": "AI 建议列为优先人工核对事项",
    "AI 维持高风险": "AI 综合判断为高关注，需人工复核",
    "AI 维持中风险": "AI 综合判断为中度关注，需人工复核",
    "本地规则等级": "规则库关注级别",
}


def audit_contract_output(
    content: str,
    contract_text: str,
    scan: ContractRuleScan,
) -> str:
    """Keep model contract suggestions within evidence and negotiation boundaries.

    The audit preserves source quotes and deterministic scan counts while softening
    unsupported numeric prescriptions, invented rights, fixed scopes and wording
    that overstates a local keyword scan as a legal conclusion.
    """
    del scan  # The scan is appended separately; source text controls safe values.
    source_values = {
        _canonical_value(item)
        for item in _HARD_VALUE_PATTERN.findall(contract_text or "")
    }
    corrections = 0
    section = ""
    headers: list[str] | None = None
    output: list[str] = []

    for original_line in (content or "").splitlines():
        line, changed = _soften_overclaims(original_line)
        corrections += changed
        stripped = line.strip()

        if stripped.startswith("## "):
            section = stripped[3:].strip()
            headers = None
            output.append(line)
            continue

        if section == "一句话结论" and stripped:
            line, changed = _ensure_ai_conclusion(line)
            corrections += changed
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
            suggestion_index = _header_index(
                headers,
                "修改建议",
                "修改方向",
                "修改建议（AI 建议）",
                "修改方向（AI 建议）",
            )
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
            f"> 系统已对 {corrections} 处可能造成误解的表述进行保守校正，包括未经合同原文支持的期限、金额、比例、阈值、固定流程或交易权利。"
            "校正后的内容仍属于待双方协商确认的 AI 建议，不代表法律标准、合同效力结论或双方已达成条款。"
        )
    return result


def _ensure_ai_conclusion(text: str) -> tuple[str, int]:
    if re.search(r"AI\s*(?:初步|综合)?判断", text):
        return text, 0
    leading = text[: len(text) - len(text.lstrip())]
    return f"{leading}AI 初步判断：{text.lstrip()}", 1


def _soften_overclaims(text: str) -> tuple[str, int]:
    result = text
    corrections = 0
    for old, new in _OVERCLAIM_REPLACEMENTS.items():
        count = result.count(old)
        if count:
            result = result.replace(old, new)
            corrections += count
    return result, corrections


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

    for pattern, replacement in _PRESCRIPTIVE_REPLACEMENTS:
        sanitized, count = pattern.subn(replacement, sanitized)
        corrections += count

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
    return bool(cells) and all(
        re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells
    )


def _header_index(headers: list[str], *names: str) -> int | None:
    for index, header in enumerate(headers):
        normalized = re.sub(r"\s+", "", header)
        if any(re.sub(r"\s+", "", name) in normalized for name in names):
            return index
    return None
