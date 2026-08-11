from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"
ROUTES = ROOT / "backend" / "project_routes.py"


def test_examples_are_a_separate_valid_asset() -> None:
    path = ASSETS / "examples.json"
    examples = json.loads(path.read_text(encoding="utf-8"))

    assert len(examples) == 12
    assert set(examples) == {
        "profile-mall",
        "profile-cbd",
        "meeting-mall",
        "meeting-cbd",
        "contract-merchant",
        "contract-ai",
        "policy-ai",
        "policy-commerce",
        "match-mall-ai",
        "match-cbd-service",
        "landing-mall",
        "landing-service-window",
    }
    assert examples["profile-mall"]["fields"]["profileName"] == "天河路商圈青年品牌联动运营小组"
    assert "会议主题：天河路商圈暑期青年品牌联动促消费活动筹备会" in examples["meeting-mall"]["fields"]["meetingInput"]

    with TestClient(app) as client:
        response = client.get("/assets/examples.json")

    assert response.status_code == 200
    assert response.json()["contract-ai"]["label"] == "AI服务采购条款"


def test_core_source_and_bundle_do_not_duplicate_example_payloads() -> None:
    source = (ASSETS / "app.js").read_text(encoding="utf-8")
    routes = ROUTES.read_text(encoding="utf-8")

    assert "const exampleScenarios = {};" in source
    assert "天河路商圈青年品牌联动运营小组" not in source
    assert "会议主题：天河路商圈暑期青年品牌联动促消费活动筹备会" not in source
    assert "_strip_embedded_examples" not in routes
    assert "_workspace_script" not in routes

    with TestClient(app) as client:
        bundle = client.get("/assets/app.js")

    assert bundle.status_code == 200
    assert bundle.headers["x-zhilink-ui-bundle"] == "2026-08-11-ui-v4-fetch-hooks-v11"
    assert "const exampleScenarios = {};" in bundle.text
    assert "天河路商圈青年品牌联动运营小组" not in bundle.text
    assert "会议主题：天河路商圈暑期青年品牌联动促消费活动筹备会" not in bundle.text
    assert "天河路商圈品牌联动促消费活动合作协议（节选）" not in bundle.text
    assert "ZHILINK_EXAMPLE_LOADER_READY" in bundle.text
    assert 'EXAMPLES_URL = "/assets/examples.json?v=20260811.1"' in bundle.text


def test_example_loader_fetches_once_on_demand_and_restores_example_context() -> None:
    loader = (ASSETS / "example-loader.js").read_text(encoding="utf-8")

    assert 'EXAMPLES_URL = "/assets/examples.json?v=20260811.1"' in loader
    assert "CONTEXT_STORAGE = contracts.storage.exampleContexts" in loader
    assert 'CONTEXT_STORAGE = "zhilian_example_contexts_v1"' not in loader
    assert 'fetch(EXAMPLES_URL, { cache: "force-cache" })' in loader
    assert "Object.assign(exampleScenarios, data)" in loader
    assert "event.preventDefault()" in loader
    assert "event.stopPropagation()" in loader
    assert 'document.addEventListener("click"' in loader
    assert "if (hasExampleContext())" in loader
    assert "ensureLoaded().catch" in loader
    assert "applyExample(exampleKey)" in loader
    assert "ZHILINK_EXAMPLE_LOADER_READY" in loader


def test_index_does_not_eagerly_request_example_payload() -> None:
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert "examples.json" not in html
    assert "example-loader.js" not in html
