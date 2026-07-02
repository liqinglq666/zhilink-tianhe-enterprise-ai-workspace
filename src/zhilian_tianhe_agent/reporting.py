# -*- coding: utf-8 -*-
"""报告导出工具。"""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Dict

try:
    from docx import Document
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml.ns import qn
    DOCX_AVAILABLE = True
except Exception:  # noqa: BLE001
    DOCX_AVAILABLE = False

from .constants import APP_FULL_NAME, LEGAL_DISCLAIMER


def build_markdown_report(results: Dict[str, str]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    parts = [
        f"# {APP_FULL_NAME}运营报告",
        f"生成时间：{now}",
        "",
        f"> {LEGAL_DISCLAIMER}",
        "",
    ]
    for title, content in results.items():
        if content:
            parts.append(f"## {title}")
            parts.append(content.strip())
            parts.append("")
    return "\n".join(parts).strip()


def build_txt_bytes(results: Dict[str, str]) -> bytes:
    return build_markdown_report(results).encode("utf-8")


def build_docx_bytes(results: Dict[str, str]) -> bytes:
    if not DOCX_AVAILABLE:
        raise RuntimeError("未安装 python-docx，无法导出DOCX。")

    doc = Document()
    styles = doc.styles
    styles["Normal"].font.name = "微软雅黑"
    styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), "微软雅黑")
    styles["Normal"].font.size = Pt(10.5)

    title = doc.add_heading(APP_FULL_NAME + "运营报告", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p = doc.add_paragraph(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph(LEGAL_DISCLAIMER)

    for section_title, content in results.items():
        if not content:
            continue
        doc.add_heading(section_title, level=1)
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("# "):
                doc.add_heading(stripped[2:], level=1)
            elif stripped.startswith("## "):
                doc.add_heading(stripped[3:], level=2)
            elif stripped.startswith("### "):
                doc.add_heading(stripped[4:], level=3)
            elif stripped.startswith("- "):
                doc.add_paragraph(stripped[2:], style="List Bullet")
            elif stripped.startswith("| "):
                # Markdown表格在Word中先作为普通文本保留，确保内容完整。
                doc.add_paragraph(stripped)
            else:
                doc.add_paragraph(stripped)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
