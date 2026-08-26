from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_v4_forms_are_loaded_directly_after_state_layer() -> None:
    with TestClient(app) as client:
        bundle = client.get("/assets/app.js")
        states = client.get("/assets/ui-v4-states.js?v=20260811.1")
        forms = client.get("/assets/ui-v4-forms.js?v=20260811.1")

    assert bundle.status_code == 200
    assert states.status_code == 200
    assert forms.status_code == 200
    assert bundle.text.index("ZHILINK_UI_V4_STATES_READY") < bundle.text.index("ZHILINK_UI_V4_FORMS_READY")
    assert "ensureForms" not in states.text
    assert "document.createElement(\"script\")" not in states.text
    assert "ZHILINK_UI_V4_FORMS_READY" in forms.text


def test_v4_form_assets_expose_consistent_business_input_hierarchy() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-forms.js?v=20260811.1")
        stylesheet = client.get("/assets/ui-v4-forms.css?v=20260811.1")

    assert script.status_code == 200
    assert stylesheet.status_code == 200
    assert "ZHILINK_UI_V4_FORMS_READY" in script.text
    assert 'title: "会议原文"' in script.text
    assert 'title: "审阅材料"' in script.text
    assert 'title: "本次政策需求"' in script.text
    assert 'title: "供需条件"' in script.text
    assert 'title: "试点配置"' in script.text
    assert 'helper.className = "ui-v4-field-helper"' in script.text
    assert 'count.className = "ui-v4-char-count"' in script.text
    assert 'error.className = "ui-v4-field-error"' in script.text
    assert 'status.className = "ui-v4-form-readiness"' in script.text
    assert 'field.setAttribute("aria-invalid", active ? "true" : "false")' in script.text
    assert 'field.setAttribute("aria-required", "true")' in script.text

    assert ".ui-v4-form-section-head" in stylesheet.text
    assert ".ui-v4-field-helper" in stylesheet.text
    assert ".ui-v4-char-count" in stylesheet.text
    assert '[aria-invalid="true"]' in stylesheet.text
    assert ".ui-v4-form-readiness" in stylesheet.text
    assert "min-height: 320px" in stylesheet.text
    assert "env(safe-area-inset-bottom)" in stylesheet.text
    assert "prefers-reduced-motion" in stylesheet.text


def test_v4_forms_match_existing_business_validation_without_adding_new_required_rules() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-forms.js?v=20260811.1")

    text = script.text
    assert 'value("meetingInput").length < 8' in text
    assert 'value("contractInput").length < 12' in text
    assert 'section === "profile" && !value("profileName") && !value("profileDemands")' in text
    assert 'section === "policy" && !value("policyDemand") && !hasProfileContext()' in text
    assert 'section === "match" && !config.fields.some(id => Boolean(value(id)))' in text
    assert 'section === "landing"' in text
    assert 'badge: "按需填写"' in text
    assert 'meetingInput: "必填"' in text
    assert 'contractInput: "必填"' in text
    assert 'policyDemand: "必填"' not in text
    assert 'offerInput: "必填"' not in text
    assert 'pilotScene: "必填"' not in text


def test_v4_forms_reuse_validation_for_readiness_without_clearing_click_errors() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-forms.js?v=20260811.1")

    text = script.text
    assert "function readinessText(section, result)" in text
    assert "function updateReadiness(section, result = null)" in text
    assert "const current = result || validate(section, { showErrors: false });" in text
    assert "status.textContent = readinessText(section, current);" in text
    assert "updateReadiness(section, result);" in text

    readiness_start = text.index("function readinessText(section, result)")
    readiness_end = text.index("function updateReadiness", readiness_start)
    assert "validate(" not in text[readiness_start:readiness_end]


def test_v4_forms_do_not_own_business_or_persistence_state() -> None:
    with TestClient(app) as client:
        script = client.get("/assets/ui-v4-forms.js?v=20260811.1")

    for forbidden in ("fetch(", "localStorage", "sessionStorage", "state.results", "setResult(", "saveConfig(", "apiStream("):
        assert forbidden not in script.text
