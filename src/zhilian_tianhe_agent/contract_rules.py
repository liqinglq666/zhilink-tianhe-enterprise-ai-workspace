# -*- coding: utf-8 -*-
"""Deterministic contract-risk pre-scan based on the local rule library."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Iterable

from .utils import load_json

MAX_EVIDENCE_PER_RULE = 3
MAX_EVIDENCE_CHARS = 220
_VALID_SEVERITIES = {"高", "中", "低"}
_WEAK_KEYWORD_ONLY = {
    "CR-DELIVERY": {"延期"},
    "CR-DATA": {"数据"},
    "CR-SCOPE": {"配合", "支持"},
}


@dataclass(frozen=True)
class ContractRule:
    rule_id: str
    name: str
    severity: str
    keywords: tuple[str, ...]
    high_risk_patterns: tuple[str, ...]
    advice: str
    confirm_questions: tuple[str, ...]


@dataclass(frozen=True)
class ContractRuleMatch:
    rule_id: str
    name: str
    severity: str
    matched_keywords: tuple[str, ...]
    evidence: tuple[str, ...]
    advice: str
    confirm_questions: tuple[str, ...]

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "category": self.name,
            "local_attention_level": self.severity,
            "matched_keywords": list(self.matched_keywords),
            "evidence": list(self.evidence),
            "advice": self.advice,
            "pending_confirmation": list(self.confirm_questions),
        }


@dataclass(frozen=True)
class ContractRuleScan:
    total_rules: int
    matches: tuple[ContractRuleMatch, ...]
    uncovered_rules: tuple[ContractRule, ...]

    @property
    def high_count(self) -> int:
        return sum(item.severity == "高" for item in self.matches)

    @property
    def medium_count(self) -> int:
        return sum(item.severity == "中" for item in self.matches)

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "scan_type": "deterministic_local_keyword_attention_scan",
            "limitations": (
                "只表示本地规则关键词预检的关注方向和规则库关注级别，不是法律结论、"
                "违法判断或合同效力判断；未命中不等于合同不存在相关条款，最终结论必须"
                "结合完整原文并由人工复核。"
            ),
            "summary": {
                "total_rules": self.total_rules,
                "matched_rules": len(self.matches),
                "high_attention_matches": self.high_count,
                "medium_attention_matches": self.medium_count,
            },
            "matches": [item.to_prompt_dict() for item in self.matches],
            "not_located_categories": [
                {
                    "rule_id": rule.rule_id,
                    "category": rule.name,
                    "pending_confirmation": list(rule.confirm_questions),
                }
                for rule in self.uncovered_rules
            ],
        }

    def to_markdown(self) -> str:
        lines = [
            "## 本地规则预检明细",
            "",
            (
                "> 本节由本地规则库确定性扫描生成，只用于定位关键词、关注方向和待确认问题；"
                "规则库关注级别不是法律风险结论，未命中也不代表合同不存在相关条款。"
                "必须结合完整原文人工复核。"
            ),
            "",
            f"- 规则总数：{self.total_rules}",
            f"- 规则库关注类别：{len(self.matches)}",
            f"- 规则库高关注提示：{self.high_count}",
            "",
        ]
        if self.matches:
            lines.extend(
                [
                    "| 规则编号 | 类别 | 规则库关注级别 | 命中关键词 | 原文证据 | 建议核对方向 |",
                    "|---|---|---|---|---|---|",
                ]
            )
            for item in self.matches:
                evidence = "；".join(_escape_table_cell(value) for value in item.evidence)
                keywords = "、".join(item.matched_keywords)
                lines.append(
                    "| {rule_id} | {name} | {severity} | {keywords} | {evidence} | {advice} |".format(
                        rule_id=_escape_table_cell(item.rule_id),
                        name=_escape_table_cell(item.name),
                        severity=_escape_table_cell(item.severity),
                        keywords=_escape_table_cell(keywords),
                        evidence=evidence,
                        advice=_escape_table_cell(item.advice),
                    )
                )
        else:
            lines.append("- 本地规则未定位到明确关键词；请勿据此判断合同无风险。")

        lines.extend(["", "### 待确认信息", ""])
        questions: list[str] = []
        for item in self.matches:
            questions.extend(f"[{item.rule_id}] {question}" for question in item.confirm_questions)
        for rule in self.uncovered_rules:
            questions.append(
                f"[{rule.rule_id}] 未在文本中稳定定位到“{rule.name}”相关条款，请确认相关内容是否缺失、使用了其他表述或位于未提供的附件中。"
            )
        for question in _unique(questions):
            lines.append(f"- [ ] {question}")
        return "\n".join(lines).strip()


@lru_cache(maxsize=1)
def load_contract_rules() -> tuple[ContractRule, ...]:
    raw = load_json("contract_risk_rules.json")
    if not isinstance(raw, list) or not raw:
        raise RuntimeError("合同风险规则库格式不合法。")

    rules: list[ContractRule] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"合同风险规则库第 {index} 项格式不合法。")
        rule_id = str(item.get("id", "")).strip()
        name = str(item.get("name", "")).strip()
        severity = str(item.get("severity", "中")).strip()
        keywords = _clean_strings(item.get("keywords", []))
        patterns = _clean_strings(item.get("high_risk_patterns", []))
        advice = str(item.get("advice", "")).strip()
        questions = _clean_strings(item.get("confirm_questions", []))
        if not rule_id or rule_id in seen_ids or not name or not keywords or not advice:
            raise RuntimeError(f"合同风险规则库第 {index} 项缺少必要字段或编号重复。")
        if severity not in _VALID_SEVERITIES:
            raise RuntimeError(f"合同风险规则 {rule_id} 的风险等级不合法。")
        seen_ids.add(rule_id)
        rules.append(
            ContractRule(
                rule_id=rule_id,
                name=name,
                severity=severity,
                keywords=keywords,
                high_risk_patterns=patterns,
                advice=advice,
                confirm_questions=questions,
            )
        )
    return tuple(rules)


def scan_contract_rules(
    contract_text: str,
    rules: Iterable[ContractRule] | None = None,
) -> ContractRuleScan:
    raw_text = contract_text or ""
    text = _normalize_text(raw_text)
    active_rules = tuple(rules or load_contract_rules())
    segments = _segments(raw_text)
    folded_text = text.casefold()
    matches: list[ContractRuleMatch] = []
    uncovered: list[ContractRule] = []

    for rule in active_rules:
        matched_keywords = tuple(
            keyword for keyword in rule.keywords if keyword.casefold() in folded_text
        )
        if not matched_keywords or _weak_keyword_match(rule, matched_keywords, folded_text):
            uncovered.append(rule)
            continue
        evidence = _evidence_for_rule(
            segments,
            matched_keywords,
            rule.high_risk_patterns,
            rule.rule_id,
        )
        evidence_text = " ".join(evidence).casefold()
        severity = (
            "高"
            if any(pattern.casefold() in evidence_text for pattern in rule.high_risk_patterns)
            else rule.severity
        )
        matches.append(
            ContractRuleMatch(
                rule_id=rule.rule_id,
                name=rule.name,
                severity=severity,
                matched_keywords=matched_keywords,
                evidence=evidence,
                advice=rule.advice,
                confirm_questions=rule.confirm_questions,
            )
        )

    matches.sort(key=lambda item: (0 if item.severity == "高" else 1, item.rule_id))
    return ContractRuleScan(
        total_rules=len(active_rules),
        matches=tuple(matches),
        uncovered_rules=tuple(uncovered),
    )


def _weak_keyword_match(
    rule: ContractRule,
    matched_keywords: tuple[str, ...],
    folded_text: str,
) -> bool:
    weak = _WEAK_KEYWORD_ONLY.get(rule.rule_id)
    if not weak or not set(matched_keywords).issubset(weak):
        return False
    return not any(pattern.casefold() in folded_text for pattern in rule.high_risk_patterns)


def _segments(text: str) -> tuple[str, ...]:
    raw_parts = re.split(r"(?<=[。！？；])|[\r\n]+", text)
    cleaned = [_trim_evidence(part) for part in raw_parts if part and part.strip()]
    return tuple(_unique(cleaned))


def _evidence_for_rule(
    segments: tuple[str, ...],
    keywords: tuple[str, ...],
    high_risk_patterns: tuple[str, ...],
    rule_id: str,
) -> tuple[str, ...]:
    ranked: list[tuple[int, int, str]] = []
    fallback: list[tuple[int, int, str]] = []
    weak_keywords = _WEAK_KEYWORD_ONLY.get(rule_id, set())

    for index, segment in enumerate(segments):
        folded = segment.casefold()
        segment_keywords = tuple(
            keyword for keyword in keywords if keyword.casefold() in folded
        )
        keyword_count = len(segment_keywords)
        if not keyword_count:
            continue

        pattern_count = sum(
            pattern.casefold() in folded for pattern in high_risk_patterns
        )
        score = keyword_count * 4 + pattern_count * 8
        item = (score, -index, _trim_evidence(segment))
        fallback.append(item)

        weak_only = (
            bool(weak_keywords)
            and set(segment_keywords).issubset(weak_keywords)
            and pattern_count == 0
        )
        if weak_only:
            continue
        ranked.append(item)

    selected = ranked or fallback
    selected.sort(reverse=True)
    evidence = [item[2] for item in selected[:MAX_EVIDENCE_PER_RULE]]
    return tuple(
        evidence
        or ("已命中关键词，但未能切分出独立证据片段，请人工查看完整原文。",)
    )


def _trim_evidence(value: str) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    if len(compact) <= MAX_EVIDENCE_CHARS:
        return compact
    return compact[: MAX_EVIDENCE_CHARS - 1].rstrip() + "…"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _clean_strings(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(_unique(str(item).strip() for item in value if str(item).strip()))


def _unique(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _escape_table_cell(value: str) -> str:
    return str(value).replace("|", "｜").replace("\n", " ").strip()
