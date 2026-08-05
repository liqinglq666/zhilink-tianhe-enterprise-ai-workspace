from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.structured_routes import register_structured_routes
from zhilian_tianhe_agent.structured_output import structure_markdown


SAMPLE = """## 一句话结论
应优先确认负责人和截止日期。[MT-01]

## 关键决策
| 事项 | 证据编号 | 状态 | 待确认信息 |
|---|---|---|---|
| 启动试点 | MT-01 | 已明确 | 无 |

## 待办事项表
| 事项 | 负责人 | 截止时间 | 证据编号 | 待确认信息 |
|---|---|---|---|---|
| 完成方案 | 待确认 | 待确认 | MT-01 | 负责人待确认 |

## 待确认信息
- 负责人和截止日期待确认。[MT-C01]
"""


def test_structured_result_extracts_sections_tables_and_confirmations():
    result = structure_markdown("meeting", SAMPLE)
    assert result.validation.valid is True
    assert result.summary.startswith("应优先确认")
    assert result.sections[1].table.columns[0] == "事项"
    assert result.pending_confirmations
    assert "MT-01" in result.evidence_ids
    assert result.source_sha256 == hashlib.sha256(SAMPLE.encode("utf-8")).hexdigest()


def test_missing_required_sections_is_reported():
    result = structure_markdown("contract", "## 一句话结论\n存在风险。[CR-PAYMENT]")
    assert result.validation.valid is False
    assert "重点风险" in result.validation.missing_required_sections
    assert any("缺少模块要求章节" in item for item in result.validation.warnings)


def test_same_source_is_deterministic_and_changed_source_changes_hash():
    first = structure_markdown("meeting", SAMPLE).model_dump()
    second = structure_markdown("meeting", SAMPLE).model_dump()
    changed = structure_markdown("meeting", SAMPLE + "\n补充").model_dump()
    assert first == second
    assert changed["source_sha256"] != first["source_sha256"]


def test_convert_endpoint_and_schema():
    app = FastAPI()
    register_structured_routes(app)
    client = TestClient(app)
    response = client.post("/api/structured/convert", json={"module": "meeting", "content": SAMPLE})
    assert response.status_code == 200
    assert response.json()["schema_version"] == "1.0"
    assert response.json()["validation"]["valid"] is True
    schema = client.get("/api/structured/schema")
    assert schema.status_code == 200
    assert "source_sha256" in schema.json()["properties"]


def test_convert_endpoint_rejects_unknown_module_and_extra_fields():
    app = FastAPI()
    register_structured_routes(app)
    client = TestClient(app)
    invalid = client.post("/api/structured/convert", json={"module": "unknown", "content": SAMPLE})
    assert invalid.status_code == 422
    extra = client.post("/api/structured/convert", json={"module": "meeting", "content": SAMPLE, "approved": True})
    assert extra.status_code == 422


def test_frontend_assets_expose_structured_controls():
    root = Path(__file__).resolve().parents[1]
    script = (root / "frontend/assets/structured-results.js").read_text(encoding="utf-8")
    assert "ZHILINK_STRUCTURED_READY" in script
    assert "/api/structured/convert" in script
    assert "data-open-structured" in script
