# -*- coding: utf-8 -*-
"""通用工具函数。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


def load_json(filename: str) -> Any:
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def safe_join(items: list[str], sep: str = "、") -> str:
    return sep.join([str(i).strip() for i in items if str(i).strip()])


def normalize_text(text: str | None) -> str:
    return (text or "").strip()


def has_meaningful_text(text: str | None, min_len: int = 8) -> bool:
    return len(normalize_text(text)) >= min_len


def compact_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """去掉空值，方便组装prompt。"""
    return {k: v for k, v in data.items() if str(v).strip() not in {"", "None", "[]"}}
