from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"
INDEX = ROOT / "frontend" / "index.html"


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
    script = (ASSETS / "model-config-save-v4.js").read_text(encoding="utf-8")

    assert "function readDraft()" in script
    assert "function commitDraft()" in script
    assert "function persistActiveConfig(config)" in script
    assert "function initialize(defaults)" in script
    assert 'window.ZHILINK_MODEL_CONFIG = Object.freeze({' in script
    assert 'await apiPost("/api/test-connection", payload)' in script
    assert "当前编辑设置，尚未保存" in script
    assert "AI 服务设置有未保存的修改" in script
    assert "restoreDraftFromActive" in script
    assert "有未保存更改" in script

    for obsolete in (
        "originalSaveConfig",
        "installCompatibilityOverrides",
        "window.getConfig =",
        "window.saveConfig =",
        "window.updateModeBadge =",
        "window.requireApiConfig =",
    ):
        assert obsolete not in script


def test_model_config_is_the_only_model_setting_persistence_owner() -> None:
    controller = (ASSETS / "model-config-save-v4.js").read_text(encoding="utf-8")
    core = (ASSETS / "app.js").read_text(encoding="utf-8")

    for marker in (
        'sessionStorage.setItem("zhilian_api_key"',
        'localStorage.setItem("zhilian_provider"',
        'localStorage.setItem("zhilian_base_url"',
        'localStorage.setItem("zhilian_model"',
        'localStorage.setItem("zhilian_temperature"',
    ):
        assert marker in controller
        assert marker not in core

    assert "function getConfig()" not in core
    assert "function saveConfig()" not in core
    assert "function updateModeBadge()" not in core
    assert "function requireApiConfig()" not in core
    assert "const controller = window.ZHILINK_MODEL_CONFIG;" in core
    assert "return controller.requireRequestConfig();" in core
    assert "controller.initialize(state.defaults)" in core
    assert '$("testConnection").addEventListener' not in core
    assert '$("clearKey").addEventListener' not in core
    assert '$("toggleKey").addEventListener' not in core


def test_model_config_clear_key_is_draft_only_until_save() -> None:
    script = (ASSETS / "model-config-save-v4.js").read_text(encoding="utf-8")

    clear_block = script[script.index(f'if (target.closest(`#${{IDS.clear}}`))'):script.index(f'if (target.closest(`#${{IDS.test}}`))')]
    assert 'key.value = ""' in clear_block
    assert "sessionStorage.removeItem" not in clear_block
    assert "保存后生效" in clear_block
    assert "已选择平台 AI 服务，保存后生效。" in clear_block
    assert "已清除访问密钥，保存后生效。" in clear_block


def test_model_config_supports_platform_and_enterprise_services_with_business_copy() -> None:
    script = (ASSETS / "model-config-save-v4.js").read_text(encoding="utf-8")

    assert "const publicModel =" in script
    assert 'fetch("/api/defaults"' in script
    assert 'return publicModel.available ? "public" : "unconfigured"' in script
    assert 'api_key: publicModel.loaded && !publicModel.userOverrideAllowed ? "" : config.api_key' in script
    assert 'publicModel.userOverrideAllowed = status?.user_override_allowed !== false' in script
    for expected in (
        'badge: "企业服务"',
        'top: "企业 AI 服务"',
        'title: "正在使用企业自有 AI 服务"',
        'badge: "平台服务"',
        'top: "AI 服务可用"',
        'title: "平台 AI 服务已就绪"',
        'top: "正在检查服务"',
        'title: "正在检查 AI 服务"',
        'badge: "未就绪"',
        'title: "AI 服务未就绪"',
        'publicModel.available ? "使用平台服务" : "清除访问密钥"',
        "当前部署未开放企业自有 AI 服务设置。",
    ):
        assert expected in script

    for obsolete in (
        'badge: "自定义 API"',
        'badge: "公共模型"',
        'top: "公共模型可用"',
        'title: "公共模型已连接"',
        "当前部署未开放用户自定义 API",
    ):
        assert obsolete not in script


def test_model_config_generation_requires_saved_enterprise_or_available_platform_service() -> None:
    script = (ASSETS / "model-config-save-v4.js").read_text(encoding="utf-8")

    assert "function requireRequestConfig()" in script
    assert "使用企业自有 AI 服务时，请完整保存访问密钥、服务地址和模型名称。" in script
    assert "AI 服务尚未就绪，请打开“AI 服务设置”完成配置后再生成。" in script
    assert "AI 服务状态仍在检查，请稍后重试。" in script
    assert "renderModelStatus" in script
    assert "zhilink:model-mode-change" in script
    assert "requireRequestConfig," in script
    assert "window.requireApiConfig" not in script


def test_model_config_owns_dynamic_state_while_customer_copy_is_native() -> None:
    script = (ASSETS / "model-config-save-v4.js").read_text(encoding="utf-8")
    stylesheet = (ASSETS / "model-config-save-v4.css").read_text(encoding="utf-8")
    html = INDEX.read_text(encoding="utf-8")

    for expected in (
        'details.id = "modelConfigAdvancedSettings"',
        'summary.id = "modelConfigAdvancedSettingsSummary"',
        'summary.textContent = "高级连接设置"',
        'note.textContent = "仅在接入企业自有 AI 服务时需要填写。普通用户无需修改。"',
        'advanced.open = mode === "custom" || mode === "unconfigured"',
        'toast("AI 服务设置已保存。")',
    ):
        assert expected in script

    assert "function applyCustomerCopy()" not in script
    assert 'setText(byId("apiDrawerTitle")' not in script
    assert "labels = new Map" not in script

    for expected in (
        '<span id="apiDrawerTitle">AI 服务设置</span>',
        '<strong>AI 服务</strong>',
        "使用平台服务时无需额外设置；企业如需接入自有服务，可在高级连接设置中维护。",
        "敏感连接信息只用于当前浏览器中的服务设置，不会写入项目或导出的业务材料。",
        '<label for="providerSelect">服务方式</label>',
        '<label for="apiKey">访问密钥</label>',
        '<label for="baseUrl">服务地址</label>',
        '<label for="modelName">模型名称</label>',
        '<label for="temperature">生成稳定性</label>',
        '>检查服务</button>',
        '>保存设置</button>',
    ):
        assert expected in html

    assert ".model-config-advanced" in stylesheet
    assert ".model-config-advanced-note" in stylesheet
    assert ".enterprise-ai-advanced" not in stylesheet


def test_model_config_styles_are_static_and_not_loaded_from_javascript() -> None:
    script = (ASSETS / "model-config-save-v4.js").read_text(encoding="utf-8")
    html = INDEX.read_text(encoding="utf-8")

    assert 'href="/assets/model-config-save-v4.css?v=20260811.1"' in html
    assert 'data-model-config-save-v4="true"' in html
    assert "function ensureStyles()" not in script
    assert 'document.createElement("link")' not in script
    assert '.rel = "stylesheet"' not in script
    assert "const VERSION =" not in script


def test_model_config_save_state_has_mobile_safe_area_and_disabled_save_feedback() -> None:
    stylesheet = (ASSETS / "model-config-save-v4.css").read_text(encoding="utf-8")
    drawer = (ASSETS / "api-drawer-v4.css").read_text(encoding="utf-8")

    assert ".model-config-draft-status" in stylesheet
    assert '[data-state="dirty"]' in stylesheet
    assert '#saveApiConfig:disabled' in stylesheet
    assert "env(safe-area-inset-bottom)" in stylesheet
    assert ".public-model-mode-notice" in drawer
