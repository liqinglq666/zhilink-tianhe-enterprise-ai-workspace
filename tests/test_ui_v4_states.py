from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_v4_state_assets_are_served_and_action_oriented() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-states.js?v=20260810.1")
        stylesheet = client.get("/assets/ui-v4-states.css?v=20260810.1")

    assert script.status_code == 200
    assert stylesheet.status_code == 200

    assert "ZHILINK_UI_V4_STATES_READY" in script.text
    assert 'document.body.classList.add("ui-v4-states")' in script.text
    assert "MutationObserver" in script.text
    assert 'element.setAttribute("aria-live", "assertive")' in script.text
    assert 'element.setAttribute("aria-live", "polite")' in script.text
    assert 'element.setAttribute("aria-busy", "true")' in script.text

    assert "还没有最近材料。完成一次业务任务后，生成结果会出现在这里。" in script.text
    assert "还没有项目。创建项目后，可保存当前工作内容和版本历史。" in script.text
    assert "当前项目还没有版本记录。保存项目后，版本历史会显示在这里。" in script.text
    assert "当前组织还没有知识条目。新建草稿并审核通过后，可用于知识检索。" in script.text

    assert '[data-ui-v4-state="empty"]' in stylesheet.text
    assert '[data-ui-v4-state="loading"]' in stylesheet.text
    assert '[data-ui-v4-state="error"]' in stylesheet.text
    assert '[data-ui-v4-state="success"]' in stylesheet.text
    assert '[data-ui-v4-state="warning"]' in stylesheet.text
    assert ".ui-v4-loading-control::before" in stylesheet.text
    assert 'button[data-ui-v4-disabled="true"]' in stylesheet.text
    assert "@media (prefers-reduced-motion: reduce)" in stylesheet.text


def test_v4_states_only_decorate_existing_ui_state() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-states.js?v=20260810.1")

    for forbidden in (
        "fetch(",
        "XMLHttpRequest",
        "sessionStorage",
        "localStorage",
        "state.results",
        "setResult",
        "saveConfig",
        "projectRequest",
    ):
        assert forbidden not in script.text

    # State decoration must not synthesize business success or performance metrics.
    for forbidden in ("98%", "提升", "节省时间", "审核准确率", "业务成功"):
        assert forbidden not in script.text


def test_v4_state_observer_does_not_watch_its_own_aria_busy_updates() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-states.js?v=20260810.1")

    assert 'attributeFilter: ["class", "disabled"]' in script.text
    assert 'attributeFilter: ["class", "disabled", "aria-busy"]' not in script.text
    assert 'button.ui-v4-loading-control:not(.loading)' in script.text
    assert 'button.dataset.uiV4BusyOwned = "true"' in script.text
