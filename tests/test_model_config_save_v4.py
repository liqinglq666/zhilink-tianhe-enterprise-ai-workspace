from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import app


def test_overlay_layer_loads_explicit_model_config_controller() -> None:
    with TestClient(app) as client:
        overlays = client.get("/assets/ui-v4-overlays.js?v=20260810.1")
        controller = client.get("/assets/model-config-save-v4.js?v=20260810.1")
        stylesheet = client.get("/assets/model-config-save-v4.css?v=20260810.1")

    assert overlays.status_code == 200
    assert controller.status_code == 200
    assert stylesheet.status_code == 200
    assert "model-config-save-v4.js" in overlays.text
    assert "data-model-config-save-v4" in overlays.text
    assert "ZHILINK_MODEL_CONFIG_SAVE_V4_READY" in controller.text


def test_model_config_uses_draft_test_and_explicit_commit() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/model-config-save-v4.js?v=20260810.1")

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
        response = client.get("/assets/model-config-save-v4.js?v=20260810.1")

    script = response.text
    clear_block = script[script.index(f'if (target.closest(`#${{IDS.clear}}`))'):script.index(f'if (target.closest(`#${{IDS.test}}`))')]
    assert 'key.value = ""' in clear_block
    assert "sessionStorage.removeItem" not in clear_block
    assert "保存后生效" in clear_block


def test_model_config_saved_status_tracks_committed_config_not_live_input() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/model-config-save-v4.js?v=20260810.1")

    script = response.text
    assert "const key = getActiveConfig().api_key.trim();" in script
    assert "renderSavedStatus" in script
    assert "请先打开“模型配置”" in script
    assert "并保存后再生成" in script


def test_model_config_save_state_has_mobile_safe_area_and_disabled_save_feedback() -> None:
    with TestClient(app) as client:
        response = client.get("/assets/model-config-save-v4.css?v=20260810.1")

    stylesheet = response.text
    assert ".model-config-draft-status" in stylesheet
    assert '[data-state="dirty"]' in stylesheet
    assert '#saveApiConfig:disabled' in stylesheet
    assert "env(safe-area-inset-bottom)" in stylesheet
