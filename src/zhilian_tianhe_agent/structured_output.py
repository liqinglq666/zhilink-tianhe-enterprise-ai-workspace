# -*- coding: utf-8 -*-
"""Deterministic, validated JSON views derived from generated Markdown."""
from __future__ import annotations

import hashlib
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

StructuredModule = Literal["profile", "meeting", "contract", "policy", "match", "landing", "report"]
SectionKind = Literal["summary", "table", "list", "checklist", "text", "mixed"]

MODULE_TITLES = {
    "profile": "企业档案", "meeting": "会议纪要", "contract": "合同审阅",
    "policy": "政策准备", "match": "供需协作", "landing": "实施计划", "report": "运营报告",
}
REQUIRED_SECTION_TOKENS = {
    "profile": ("一句话结论", "企业画像", "主要运营痛点", "待确认信息"),
    "meeting": ("一句话结论", "关键决策", "待办事项", "待确认信息"),
    "contract": ("一句话结论", "重点风险", "待确认", "免责声明"),
    "policy": ("一句话结论", "推荐关注方向", "真实政策核验", "待补齐"),
    "match": ("一句话结论", "供需标签", "合作方案", "待确认信息"),
    "landing": ("一句话结论", "标准 SOP", "数据与安全边界", "待确认信息"),
    "report": ("一句话结论", "关键事项", "待确认信息", "风险声明"),
}
EVIDENCE_RE = re.compile(r"(?<![A-Z0-9_-])(?:CR-[A-Z][A-Z0-9_-]*|[A-Z]{2,4}-C?\d{2})(?![A-Z0-9_-])")
HEADING_RE = re.compile(r"^##\s+(.+?)\s*$")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")
LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
CHECK_RE = re.compile(r"^\s*[-*+]\s+\[([ xX])\]\s+(.*)$")
MAX_SECTION_CHARS = 12000
MAX_ITEM_CHARS = 1200
MAX_SECTIONS = 40
MAX_ITEMS = 200


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StructuredTable(StrictModel):
    columns: list[str] = Field(default_factory=list, max_length=20)
    rows: list[list[str]] = Field(default_factory=list, max_length=200)

    @field_validator("columns")
    @classmethod
    def validate_columns(cls, value: list[str]) -> list[str]:
        return [_clip(item, 200) for item in value]

    @field_validator("rows")
    @classmethod
    def validate_rows(cls, value: list[list[str]]) -> list[list[str]]:
        return [[_clip(cell, 1000) for cell in row[:20]] for row in value]


class StructuredItem(StrictModel):
    id: str = Field(max_length=20)
    text: str = Field(max_length=MAX_ITEM_CHARS)
    section_id: str = Field(max_length=20)
    evidence_ids: list[str] = Field(default_factory=list, max_length=30)
    status: str = Field(default="", max_length=100)


class StructuredSection(StrictModel):
    id: str = Field(max_length=20)
    title: str = Field(max_length=200)
    kind: SectionKind
    text: str = Field(default="", max_length=MAX_SECTION_CHARS)
    items: list[str] = Field(default_factory=list, max_length=MAX_ITEMS)
    table: StructuredTable | None = None
    evidence_ids: list[str] = Field(default_factory=list, max_length=100)


class StructuredValidation(StrictModel):
    valid: bool
    warnings: list[str] = Field(default_factory=list, max_length=30)
    missing_required_sections: list[str] = Field(default_factory=list, max_length=20)
    section_count: int = Field(ge=0, le=MAX_SECTIONS)
    heading_count: int = Field(ge=0, le=MAX_SECTIONS)
    evidence_reference_count: int = Field(ge=0, le=10000)
    pending_confirmation_count: int = Field(ge=0, le=MAX_ITEMS)


class StructuredResult(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    module: StructuredModule
    title: str = Field(max_length=200)
    summary: str = Field(default="", max_length=2000)
    sections: list[StructuredSection] = Field(default_factory=list, max_length=MAX_SECTIONS)
    facts: list[StructuredItem] = Field(default_factory=list, max_length=MAX_ITEMS)
    inferences: list[StructuredItem] = Field(default_factory=list, max_length=MAX_ITEMS)
    risks: list[StructuredItem] = Field(default_factory=list, max_length=MAX_ITEMS)
    actions: list[StructuredItem] = Field(default_factory=list, max_length=MAX_ITEMS)
    pending_confirmations: list[StructuredItem] = Field(default_factory=list, max_length=MAX_ITEMS)
    evidence_ids: list[str] = Field(default_factory=list, max_length=500)
    source_sha256: str = Field(min_length=64, max_length=64)
    validation: StructuredValidation


def _clip(value: object, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def _evidence_ids(text: str, limit: int = 500) -> list[str]:
    return list(dict.fromkeys(EVIDENCE_RE.findall(text or "")))[:limit]


def _split_cells(line: str) -> list[str]:
    return [_clip(cell, 1000) for cell in line.strip().strip("|").split("|")][:20]


def _parse_table(lines: list[str]) -> StructuredTable | None:
    for index in range(len(lines) - 1):
        if "|" not in lines[index] or not TABLE_SEPARATOR_RE.match(lines[index + 1]):
            continue
        columns = _split_cells(lines[index])
        rows: list[list[str]] = []
        for raw in lines[index + 2:]:
            if "|" not in raw:
                break
            cells = _split_cells(raw)
            if cells:
                rows.append((cells + [""] * len(columns))[:len(columns)])
            if len(rows) >= 200:
                break
        return StructuredTable(columns=columns, rows=rows)
    return None


def _parse_items(lines: list[str]) -> tuple[list[str], bool]:
    items: list[str] = []
    checklist = False
    for raw in lines:
        check = CHECK_RE.match(raw)
        if check:
            checklist = True
            items.append(_clip(f"[{'x' if check.group(1).lower() == 'x' else ' '}] {check.group(2)}", MAX_ITEM_CHARS))
            continue
        match = LIST_RE.match(raw)
        if match:
            items.append(_clip(match.group(1), MAX_ITEM_CHARS))
        if len(items) >= MAX_ITEMS:
            break
    return items, checklist


def _section_kind(table: StructuredTable | None, items: list[str], checklist: bool, title: str) -> SectionKind:
    if "一句话结论" in title:
        return "summary"
    if table and items:
        return "mixed"
    if table:
        return "table"
    if checklist:
        return "checklist"
    if items:
        return "list"
    return "text"


def _section_text(lines: list[str]) -> str:
    useful: list[str] = []
    for raw in lines:
        if TABLE_SEPARATOR_RE.match(raw) or raw.strip().startswith("|"):
            continue
        if CHECK_RE.match(raw) or LIST_RE.match(raw):
            continue
        if raw.strip():
            useful.append(raw.strip())
    return _clip("\n".join(useful), MAX_SECTION_CHARS)


def _section_fragments(section: StructuredSection) -> list[str]:
    fragments = list(section.items)
    if section.text:
        fragments.extend(part.strip() for part in re.split(r"[\n。；;]+", section.text) if part.strip())
    if section.table:
        fragments.extend(" | ".join(cell for cell in row if cell) for row in section.table.rows)
    return [_clip(item, MAX_ITEM_CHARS) for item in fragments if _clip(item, MAX_ITEM_CHARS)][:MAX_ITEMS]


def _make_items(section: StructuredSection, fragments: list[str], prefix: str) -> list[StructuredItem]:
    output: list[StructuredItem] = []
    seen: set[str] = set()
    for fragment in fragments:
        text = _clip(fragment, MAX_ITEM_CHARS)
        if not text or text in seen:
            continue
        seen.add(text)
        status = ""
        if "AI 推断" in text:
            status = "AI 推断"
        elif any(token in text for token in ("原文事实", "输入事实", "已明确", "已确认")):
            status = "输入事实"
        elif "待确认" in text:
            status = "待确认"
        output.append(StructuredItem(
            id=f"{prefix}{len(output)+1:02d}", text=text, section_id=section.id,
            evidence_ids=_evidence_ids(text, 30), status=status,
        ))
        if len(output) >= MAX_ITEMS:
            break
    return output


def _dedupe(items: list[StructuredItem]) -> list[StructuredItem]:
    seen: set[tuple[str, str]] = set()
    output: list[StructuredItem] = []
    for item in items:
        key = (item.section_id, item.text)
        if key in seen:
            continue
        seen.add(key)
        output.append(item.model_copy(update={"id": f"{item.id[:1]}{len(output)+1:02d}"}))
        if len(output) >= MAX_ITEMS:
            break
    return output


def structure_markdown(module: StructuredModule, markdown: str) -> StructuredResult:
    source = str(markdown or "").replace("\r\n", "\n").replace("\r", "\n")
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    raw_sections: list[tuple[str, list[str]]] = []
    title, body = "核心内容", []
    heading_count = 0
    for raw in source.split("\n"):
        heading = HEADING_RE.match(raw.strip())
        if heading:
            heading_count += 1
            if body or raw_sections:
                raw_sections.append((title, body))
            title, body = _clip(heading.group(1), 200), []
        else:
            body.append(raw)
    if body or not raw_sections:
        raw_sections.append((title, body))

    sections: list[StructuredSection] = []
    for section_title, lines in raw_sections[:MAX_SECTIONS]:
        if not any(item.strip() for item in lines):
            continue
        table = _parse_table(lines)
        items, checklist = _parse_items(lines)
        sections.append(StructuredSection(
            id=f"S{len(sections)+1:02d}",
            title=section_title,
            kind=_section_kind(table, items, checklist, section_title),
            text=_section_text(lines),
            items=items,
            table=table,
            evidence_ids=_evidence_ids("\n".join(lines), 100),
        ))

    summary = ""
    for section in sections:
        if "一句话结论" in section.title:
            summary = section.text or (section.items[0] if section.items else "")
            if not summary and section.table and section.table.rows:
                summary = "；".join(section.table.rows[0])
            break
    if not summary and sections:
        summary = sections[0].text or (sections[0].items[0] if sections[0].items else "")

    facts: list[StructuredItem] = []
    inferences: list[StructuredItem] = []
    risks: list[StructuredItem] = []
    actions: list[StructuredItem] = []
    pending: list[StructuredItem] = []
    for section in sections:
        fragments = _section_fragments(section)
        if any(token in section.title for token in ("风险", "提醒", "问题")):
            risks.extend(_make_items(section, fragments, "R"))
        if any(token in section.title for token in ("动作", "建议", "议题", "清单", "材料准备", "实施")):
            actions.extend(_make_items(section, fragments, "A"))
        pending_fragments = [item for item in fragments if "待确认" in item]
        if any(token in section.title for token in ("待确认", "未定位", "待补齐")):
            pending_fragments = fragments
        pending.extend(_make_items(section, pending_fragments, "C"))
        facts.extend(_make_items(section, [x for x in fragments if any(t in x for t in ("原文事实", "输入事实", "已明确", "已确认"))], "F"))
        inferences.extend(_make_items(section, [x for x in fragments if "AI 推断" in x], "I"))

    facts, inferences, risks, actions, pending = map(_dedupe, (facts, inferences, risks, actions, pending))
    evidence = _evidence_ids(source)
    warnings: list[str] = []
    if not summary:
        warnings.append("未识别到一句话结论。")
    if not sections:
        warnings.append("未识别到可用章节。")
    if not evidence:
        warnings.append("未识别到证据编号；事实性结论需要人工复核。")
    if not heading_count:
        warnings.append("未识别到 Markdown 二级标题。")
    if heading_count > MAX_SECTIONS:
        warnings.append(f"章节数量超过 {MAX_SECTIONS}，结构化结果仅保留前 {MAX_SECTIONS} 个章节。")
    if not pending and any(token in source for token in ("待确认", "未定位", "待补齐")):
        warnings.append("文本包含待确认表述，但未能稳定提取为结构化条目。")
    titles = [section.title for section in sections]
    missing_required = [
        token for token in REQUIRED_SECTION_TOKENS[module]
        if not any(token in title for title in titles)
    ]
    if missing_required:
        warnings.append("缺少模块要求章节：" + "、".join(missing_required))

    return StructuredResult(
        module=module,
        title=f"{MODULE_TITLES[module]}结构化结果",
        summary=_clip(summary, 2000),
        sections=sections,
        facts=facts,
        inferences=inferences,
        risks=risks,
        actions=actions,
        pending_confirmations=pending,
        evidence_ids=evidence,
        source_sha256=digest,
        validation=StructuredValidation(
            valid=bool(summary and sections and heading_count and not missing_required),
            warnings=warnings,
            missing_required_sections=missing_required,
            section_count=len(sections),
            heading_count=min(heading_count, MAX_SECTIONS),
            evidence_reference_count=len(evidence),
            pending_confirmation_count=len(pending),
        ),
    )
