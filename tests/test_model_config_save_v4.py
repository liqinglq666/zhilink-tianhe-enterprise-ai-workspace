from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_bundle_loads_explicit_model_config_controller_after_native_drawer() -> None:
    with TestClient(app) as client:
        bundle = client.get("/assets/app.js")
        overlays = client.get("/assets/ui-v4-overlays.js?v=20260811.1")
        controller = client.get("/assets/model-config-save-v4.js?v=20260811.1")
        stylesheet = client.get("/assets/model-config-save-v4.css?v=20260811.1")

    assert bundle.status_code == 200
    assert overlays.status_code == 200
    assert controller.status_code == 200
    assert stylesheet.status_code == 200
    assert bundle.text.index("ZHILINK_API_DRAWER_V4_READY") < bundle.text.index("ZHILINK_MODEL_CONFIG_SAVE_V4_READY")
    assert "model-config-save-v4.js" not in overlays.text
    assert "data-model-config-save-v4" not in overlays.text
    assert "ZHILINK_MODEL_CONFIG_SAVE_V4_READY" in controller.text
    assert 'close: () => document.getElementById("uiV4ApiClose")' in overlays.text
    assert "liveApiClose" not in overlays.text


def test_model_config_uses_draft_test_and_explicit_commit() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/model-config-save-v4.js?v=20260811.1")

    script = response.text
    assert "function readDraft()" in script
    assert "function commitDraft()" in script
    assert "originalSaveConfig" in script
    assert 'window.saveConfig = function saveConfigWithoutImplicitPersistence()' in script
    assert 'window.getConfig = getActiveRequestConfig' in script
    assert 'await apiPost("/api/test-connection", payload)' in script
    assert "当前编辑内容，尚未保存" in script
    assert "模型配置有未保存的修改" in script
    assert "restoreDraftFromActive" in script
    assert "有未保存更改" in script


def test_model_config_clear_key_is_draft_only_until_save() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/model-config-save-v4.js?v=20260811.1")

    script = response.text
    clear_block = script[script.index(f'if (target.closest(`#${{IDS.clear}}`))'):script.index(f'if (target.closest(`#${{IDS.test}}`))')]
    assert 'key.value = ""' in clear_block
    assert "sessionStorage.removeItem" not in clear_block
    assert "保存后生效" in clear_block


def test_model_config_supports_public_model_without_browser_key() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/model-config-save-v4.js?v=20260811.1")

    script = response.text
    assert "const publicModel =" in script
    assert 'fetch("/api/defaults"' in script
    assert 'return publicModel.available ? "public" : "unconfigured"' in script
    assert 'api_key: publicModel.loaded && !publicModel.userOverrideAllowed ? "" : config.api_key' in script
    assert 'publicModel.userOverrideAllowed = status?.user_override_allowed !== false' in script
    assert 'publicModel.available ? "恢复公共模型" : "清空 API Key"' in script
    assert "当前部署未开放用户自定义 API" in script
    assert "公共模型已连接" in script


def test_model_config_generation_requires_saved_custom_or_available_public_model() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/model-config-save-v4.js?v=20260811.1")

    script = response.text
    assert 'window.requireApiConfig = function requireAvailableModel()' in script
    assert "使用自定义 API 时，请完整保存 API Key、Base URL 和模型名称" in script
    assert "当前公共模型尚未配置" in script
    assert "renderModelStatus" in script
    assert "zhilink:model-mode-change" in script


def test_model_config_save_state_has_mobile_safe_area_and_disabled_save_feedback() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/model-config-save-v4.css?v=20260811.1")
        drawer = client.get("/assets/api-drawer-v4.css?v=20260811.1")

    stylesheet = response.text
    assert ".model-config-draft-status" in stylesheet
    assert '[data-state="dirty"]' in stylesheet
    assert '#saveApiConfig:disabled' in stylesheet
    assert "env(safe-area-inset-bottom)" in stylesheet
    assert ".public-model-mode-notice" in drawer.text
