/* UI V4 model config: draft -> test -> explicit save. */
(() => {
  const VERSION = "20260810.1";
  const IDS = {
    panel: "apiPanel",
    provider: "providerSelect",
    apiKey: "apiKey",
    baseUrl: "baseUrl",
    model: "modelName",
    temperature: "temperature",
    temperatureValue: "tempValue",
    save: "saveApiConfig",
    test: "testConnection",
    clear: "clearKey",
    close: "liveApiClose",
    backdrop: "liveApiBackdrop",
    result: "connectionResult",
  };

  const originalSaveConfig = typeof window.saveConfig === "function" ? window.saveConfig : null;
  const originalGetConfig = typeof window.getConfig === "function" ? window.getConfig : null;
  let activeConfig = null;
  let sessionOpen = false;
  let dirty = false;
  let observer = null;

  function byId(id) { return document.getElementById(id); }

  function ensureStyles() {
    if (document.querySelector("link[data-model-config-save-v4]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `/assets/model-config-save-v4.css?v=${VERSION}`;
    link.dataset.modelConfigSaveV4 = "true";
    document.head.appendChild(link);
  }

  function readDraft() {
    return {
      provider: byId(IDS.provider)?.value || "",
      api_key: byId(IDS.apiKey)?.value.trim() || "",
      base_url: byId(IDS.baseUrl)?.value.trim() || "",
      model: byId(IDS.model)?.value.trim() || "",
      temperature: Number(byId(IDS.temperature)?.value || 0.35),
    };
  }

  function cloneConfig(config) {
    return {
      provider: String(config?.provider || ""),
      api_key: String(config?.api_key || ""),
      base_url: String(config?.base_url || ""),
      model: String(config?.model || ""),
      temperature: Number(config?.temperature ?? 0.35),
    };
  }

  function captureActiveFromStorage() {
    const draft = readDraft();
    activeConfig = {
      provider: localStorage.getItem("zhilian_provider") || draft.provider,
      api_key: sessionStorage.getItem("zhilian_api_key") || "",
      base_url: localStorage.getItem("zhilian_base_url") || draft.base_url,
      model: localStorage.getItem("zhilian_model") || draft.model,
      temperature: Number(localStorage.getItem("zhilian_temperature") || draft.temperature || 0.35),
    };
    return activeConfig;
  }

  function getActiveConfig() {
    if (!activeConfig) captureActiveFromStorage();
    return cloneConfig(activeConfig);
  }

  function getActiveRequestConfig() {
    const config = getActiveConfig();
    return {
      api_key: config.api_key,
      base_url: config.base_url,
      model: config.model,
      temperature: config.temperature,
    };
  }

  function sameConfig(left, right) {
    const a = cloneConfig(left);
    const b = cloneConfig(right);
    return a.provider === b.provider
      && a.api_key === b.api_key
      && a.base_url === b.base_url
      && a.model === b.model
      && Number(a.temperature) === Number(b.temperature);
  }

  function renderSavedStatus() {
    const key = getActiveConfig().api_key.trim();
    const badge = byId("modeBadge");
    const homeStatus = byId("homeApiStatus");
    const topStatus = byId("topApiStatus");
    if (key) {
      if (badge) { badge.textContent = "已配置"; badge.className = "status-badge ai"; }
      if (homeStatus) homeStatus.textContent = "已配置";
      if (topStatus) { topStatus.textContent = "API 已配置"; topStatus.className = "top-status ready"; }
    } else {
      if (badge) { badge.textContent = "待配置"; badge.className = "status-badge local"; }
      if (homeStatus) homeStatus.textContent = "待配置";
      if (topStatus) { topStatus.textContent = "API 待配置"; topStatus.className = "top-status pending"; }
    }
  }

  function ensureDraftIndicator() {
    const footer = document.querySelector(`#${IDS.panel} .api-drawer-footer`);
    if (!footer) return null;
    let indicator = byId("modelConfigDraftStatus");
    if (!indicator) {
      indicator = document.createElement("span");
      indicator.id = "modelConfigDraftStatus";
      indicator.className = "model-config-draft-status";
      footer.prepend(indicator);
    }
    return indicator;
  }

  function updateDraftState() {
    if (!sessionOpen) return;
    dirty = !sameConfig(readDraft(), getActiveConfig());
    const indicator = ensureDraftIndicator();
    if (indicator) {
      indicator.textContent = dirty ? "有未保存更改" : "已保存";
      indicator.dataset.state = dirty ? "dirty" : "saved";
    }
    const save = byId(IDS.save);
    if (save) save.disabled = !dirty;
  }

  function restoreDraftFromActive() {
    const config = getActiveConfig();
    const provider = byId(IDS.provider);
    const key = byId(IDS.apiKey);
    const baseUrl = byId(IDS.baseUrl);
    const model = byId(IDS.model);
    const temperature = byId(IDS.temperature);
    if (provider && config.provider) provider.value = config.provider;
    if (key) key.value = config.api_key;
    if (baseUrl) baseUrl.value = config.base_url;
    if (model) model.value = config.model;
    if (temperature) temperature.value = String(config.temperature);
    if (byId(IDS.temperatureValue)) byId(IDS.temperatureValue).textContent = String(config.temperature);
    dirty = false;
    updateDraftState();
  }

  function beginEditSession() {
    if (sessionOpen) return;
    if (!activeConfig) captureActiveFromStorage();
    sessionOpen = true;
    restoreDraftFromActive();
    const result = byId(IDS.result);
    if (result) result.textContent = "";
    updateDraftState();
  }

  function endEditSession() {
    sessionOpen = false;
    dirty = false;
  }

  function commitDraft() {
    activeConfig = cloneConfig(readDraft());
    if (originalSaveConfig) originalSaveConfig();
    renderSavedStatus();
    dirty = false;
    updateDraftState();
  }

  function shouldAllowClose() {
    if (!sessionOpen || !dirty) return true;
    const discard = window.confirm("模型配置有未保存的修改。要放弃这些修改吗？");
    if (!discard) return false;
    restoreDraftFromActive();
    return true;
  }

  async function testDraftConnection() {
    const button = byId(IDS.test);
    const result = byId(IDS.result);
    const draft = readDraft();
    if (!draft.api_key || !draft.base_url || !draft.model) {
      if (result) result.textContent = "请先填写 API Key、Base URL 和模型名称，再测试连接。";
      return;
    }
    try {
      if (typeof setLoading === "function") setLoading(button, true, "测试中...");
      const payload = {
        api_key: draft.api_key,
        base_url: draft.base_url,
        model: draft.model,
        temperature: draft.temperature,
      };
      const response = typeof apiPost === "function"
        ? await apiPost("/api/test-connection", payload)
        : null;
      if (!response) throw new Error("连接测试不可用。");
      if (result) {
        result.textContent = response.ok
          ? `连接成功（当前编辑内容，尚未保存）：${response.content || response.mode || "模型可用"}`
          : `连接失败：${response.error || "模型接口不可用"}`;
      }
    } catch (error) {
      if (result) result.textContent = `连接失败：${error.message || String(error)}`;
    } finally {
      if (typeof setLoading === "function") setLoading(button, false);
    }
  }

  function installCompatibilityOverrides() {
    window.getConfig = getActiveRequestConfig;
    window.saveConfig = function saveConfigWithoutImplicitPersistence() {
      return getActiveRequestConfig();
    };
    window.updateModeBadge = renderSavedStatus;
    window.requireApiConfig = function requireSavedApiConfig() {
      const config = getActiveRequestConfig();
      if (!config.api_key || !config.base_url || !config.model) {
        throw new Error("请先打开“模型配置”，填写 API Key、Base URL 和模型名称并保存后再生成。当前版本不提供本地示例生成。");
      }
      return config;
    };
  }

  function handleClick(event) {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;

    if (target.closest(`#${IDS.clear}`)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      const key = byId(IDS.apiKey);
      if (key) key.value = "";
      updateDraftState();
      if (typeof toast === "function") toast("已从当前编辑内容中清空 API Key，保存后生效。" );
      return;
    }

    if (target.closest(`#${IDS.test}`)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      testDraftConnection();
      return;
    }

    if (target.closest(`#${IDS.save}`)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      commitDraft();
      if (typeof toast === "function") toast("模型配置已保存。" );
      const close = byId(IDS.close);
      if (close) close.click();
      return;
    }

    if (target.closest(`#${IDS.close}`) || target.closest(`#${IDS.backdrop}`)) {
      if (!shouldAllowClose()) {
        event.preventDefault();
        event.stopImmediatePropagation();
        return;
      }
      endEditSession();
    }
  }

  function handleDraftChange(event) {
    const panel = byId(IDS.panel);
    if (!sessionOpen || !panel || !(event.target instanceof Node) || !panel.contains(event.target)) return;
    window.setTimeout(updateDraftState, 0);
  }

  function installObserver() {
    if (observer || !document.body) return;
    let wasOpen = document.body.classList.contains("live-api-open");
    if (wasOpen) beginEditSession();
    observer = new MutationObserver(() => {
      const open = document.body.classList.contains("live-api-open");
      if (open && !wasOpen) beginEditSession();
      if (!open && wasOpen) endEditSession();
      wasOpen = open;
    });
    observer.observe(document.body, { attributes: true, attributeFilter: ["class"] });
  }

  function start() {
    ensureStyles();
    installCompatibilityOverrides();
    document.addEventListener("click", handleClick, true);
    document.addEventListener("input", handleDraftChange, true);
    document.addEventListener("change", handleDraftChange, true);
    installObserver();
    window.setTimeout(() => {
      if (!activeConfig && byId(IDS.provider)?.options?.length) captureActiveFromStorage();
      renderSavedStatus();
    }, 0);
    window.ZHILINK_MODEL_CONFIG_SAVE_V4_READY = true;
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
