from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_v4_state_assets_are_served_and_presentation_only() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-states.js?v=20260811.1")
        runtime = client.get("/assets/ui-v4-runtime.js?v=20260811.1")
        stylesheet = client.get("/assets/ui-v4-states.css?v=20260811.1")

    assert script.status_code == 200
    assert runtime.status_code == 200
    assert stylesheet.status_code == 200

    assert "ZHILINK_UI_V4_STATES_READY" in script.text
    assert 'document.body.classList.add("ui-v4-states")' in script.text
    assert "MutationObserver" not in script.text
    assert 'window.ZHILINK_UI_V4_RUNTIME?.subscribe?.(() => sync(document), { immediate: false })' in script.text
    assert "new MutationObserver" in runtime.text
    assert 'element.setAttribute("aria-live", "assertive")' in script.text
    assert 'element.setAttribute("aria-live", "polite")' in script.text
    assert 'element.setAttribute("aria-busy", "true")' in script.text

    assert "actionOrientedEmptyCopy" not in script.text
    assert "还没有最近材料。完成一次业务任务后，生成结果会出现在这里。" not in script.text
    assert "还没有项目。创建项目后，可保存当前工作内容和版本历史。" not in script.text
    assert "当前项目还没有版本记录。保存项目后，版本历史会显示在这里。" not in script.text
    assert "当前组织还没有知识条目。新建草稿并审核通过后，可用于知识检索。" not in script.text

    assert '[data-ui-v4-state="empty"]' in stylesheet.text
    assert '[data-ui-v4-state="loading"]' in stylesheet.text
    assert '[data-ui-v4-state="error"]' in stylesheet.text
    assert '[data-ui-v4-state="success"]' in stylesheet.text
    assert '[data-ui-v4-state="warning"]' in stylesheet.text
    assert ".ui-v4-loading-control::before" in stylesheet.text
    assert "button:disabled" in stylesheet.text
    assert "input:disabled" in stylesheet.text
    assert "select:disabled" in stylesheet.text
    assert "textarea:disabled" in stylesheet.text
    assert "data-ui-v4-disabled" not in stylesheet.text
    assert "@media (prefers-reduced-motion: reduce)" in stylesheet.text


def test_business_owners_keep_their_own_empty_state_copy() -> None:
    project = (ASSETS / "project-storage.js").read_text(encoding="utf-8")
    knowledge = (ASSETS / "knowledge-base.js").read_text(encoding="utf-8")
    app_script = (ASSETS / "app.js").read_text(encoding="utf-8")
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "当前工作区还没有项目。" in project
    assert "该项目还没有版本记录。" in project
    assert "当前组织还没有可见的知识条目。" in knowledge
    assert "选择一个知识条目，或新建草稿。" in knowledge
    assert "暂无生成材料。进入业务模块完成一次任务后，这里会自动显示最近材料。" in app_script
    assert "还没有最近结果。完成一次业务任务后，这里会显示你的最新材料。" in html


def test_v4_states_only_decorate_existing_ui_state() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-states.js?v=20260811.1")

    for forbidden in (
        "fetch(", "XMLHttpRequest", "sessionStorage", "localStorage", "state.results", "setResult", "saveConfig", "projectRequest",
    ):
        assert forbidden not in script.text

    for forbidden in ("98%", "提升", "节省时间", "审核准确率", "业务成功"):
        assert forbidden not in script.text

    assert "decorateDisabledControls" not in script.text
    assert "uiV4Disabled" not in script.text
    assert "data-ui-v4-disabled" not in script.text


def test_shared_runtime_observer_does_not_watch_aria_busy_updates() -> None:
    with TestClient(app) as client:
        runtime = client.get("/assets/ui-v4-runtime.js?v=20260811.1")
        states = client.get("/assets/ui-v4-states.js?v=20260811.1")

    assert 'attributeFilter: ["class", "hidden", "aria-hidden", "aria-expanded", "disabled"]' in runtime.text
    assert '"aria-busy"' not in runtime.text
    assert 'button.ui-v4-loading-control:not(.loading)' in states.text
    assert 'button.dataset.uiV4BusyOwned = "true"' in states.text
