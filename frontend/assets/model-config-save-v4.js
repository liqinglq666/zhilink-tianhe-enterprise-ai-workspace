/* UI V4 model config: sole owner of AI service draft, persistence and request configuration. */
(() => {
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
    toggle: "toggleKey",
    clear: "clearKey",
    close: "uiV4ApiClose",
    backdrop: "uiV4ApiBackdrop",
    result: "connectionResult",
  };

  let activeConfig = null;
  let providerPresets = {};
  let sessionOpen = false;
  let dirty = false;
  let observer = null;
  let started = false;
  let initialized = false;

  const publicModel = {
    loaded: false,
    available: false,
    provider: "",
    model: "",
    userOverrideAllowed: true,
  };

  function byId(id) { return document.getElementById(id); }

  function cloneConfig(config) {
    return {
      provider: String(config?.provider || ""),
      api_key: String(config?.api_key || ""),
      base_url: String(config?.base_url || ""),
      model: String(config?.model || ""),
      temperature: Number(config?.temperature ?? 0.35),
    };
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

  function persistActiveConfig(config) {
    const current = cloneConfig(config);
    if (current.api_key) sessionStorage.setItem("zhilian_api_key", current.api_key);
    else sessionStorage.removeItem("zhilian_api_key");
    localStorage.setItem("zhilian_provider", current.provider);
    localStorage.setItem("zhilian_base_url", current.base_url);
    localStorage.setItem("zhilian_model", current.model);
    localStorage.setItem("zhilian_temperature", String(current.temperature));
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
      api_key: publicModel.loaded && !publicModel.userOverrideAllowed ? "" : config.api_key,
      base_url: config.base_url,
      model: config.model,
      temperature: config.temperature,
    };
  }

  function requireRequestConfig() {
    const config = getActiveRequestConfig();
    if (config.api_key) {
      if (!config.base_url || !config.model) {
        throw new Error("使用企业自有 AI 服务时，请完整保存访问密钥、服务地址和模型名称。");
      }
      return config;
    }
    if (!publicModel.loaded) {
      throw new Error("AI 服务状态仍在检查，请稍后重试。");
    }
    if (!publicModel.available) {
      throw new Error("AI 服务尚未就绪，请打开“AI 服务设置”完成配置后再生成。");
    }
    return config;
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

  function modelMode(config = getActiveConfig()) {
    if (publicModel.loaded && !publicModel.userOverrideAllowed) return publicModel.available ? "public" : "unconfigured";
    if (String(config.api_key || "").trim()) return "custom";
    if (!publicModel.loaded) return "checking";
    return publicModel.available ? "public" : "unconfigured";
  }

  function modeCopy(mode) {
    if (mode === "custom") return {
      badge: "企业服务",
      top: "企业 AI 服务",
      title: "正在使用企业自有 AI 服务",
      detail: "连接信息仅用于企业自有服务，不会写入业务材料。",
    };
    if (mode === "public") return {
      badge: "平台服务",
      top: "AI 服务可用",
      title: "平台 AI 服务已就绪",
      detail: "当前服务可直接使用，无需额外设置。",
    };
    if (mode === "checking") return {
      badge: "检查中",
      top: "正在检查服务",
      title: "正在检查 AI 服务",
      detail: "请稍候，系统正在确认服务状态。",
    };
    return {
      badge: "未就绪",
      top: "AI 服务未就绪",
      title: "AI 服务未就绪",
      detail: "请联系管理员，或在高级连接设置中配置企业自有 AI 服务。",
    };
  }

  function ensureAdvancedSettings() {
    const body = byId("apiPanelBody");
    const fields = body?.querySelector(".api-drawer-fields");
    if (!body || !fields) return null;
    let details = byId("modelConfigAdvancedSettings");
    if (details) return details;
    details = document.createElement("details");
    details.id = "modelConfigAdvancedSettings";
    details.className = "model-config-advanced";
    const summary = document.createElement("summary");
    summary.id = "modelConfigAdvancedSettingsSummary";
    summary.textContent = "高级连接设置";
    const note = document.createElement("p");
    note.className = "model-config-advanced-note";
    note.textContent = "仅在接入企业自有 AI 服务时需要填写。普通用户无需修改。";
    fields.before(details);
    details.append(summary, note, fields);
    return details;
  }

  function ensurePublicNotice() {
    const body = byId("apiPanelBody");
    const fields = body?.querySelector(".api-drawer-fields");
    if (!body || !fields) return null;
    const advanced = ensureAdvancedSettings();
    let notice = byId("publicModelModeNotice");
    if (!notice) {
      notice = document.createElement("div");
      notice.id = "publicModelModeNotice";
      notice.className = "public-model-mode-notice";
      notice.innerHTML = "<strong data-public-model-title></strong><span data-public-model-detail></span>";
      body.insertBefore(notice, advanced || fields);
    }
    return notice;
  }

  function renderModelStatus() {
    if (!document.body) return;
    const mode = modelMode();
    const copy = modeCopy(mode);
    const badge = byId("modeBadge");
    const homeStatus = byId("homeApiStatus");
    const topStatus = byId("topApiStatus");
    if (badge) {
      badge.textContent = copy.badge;
      badge.className = mode === "unconfigured" || mode === "checking" ? "status-badge local" : "status-badge ai";
    }
    if (homeStatus) homeStatus.textContent = copy.badge;
    if (topStatus) {
      topStatus.textContent = copy.top;
      topStatus.className = mode === "unconfigured" ? "top-status pending" : "top-status ready";
    }
    document.body.dataset.modelMode = mode;
    const notice = ensurePublicNotice();
    if (notice) {
      notice.dataset.mode = mode;
      const title = notice.querySelector("[data-public-model-title]");
      const detail = notice.querySelector("[data-public-model-detail]");
      if (title) title.textContent = copy.title;
      if (detail) detail.textContent = copy.detail;
    }
    const advanced = ensureAdvancedSettings();
    if (advanced) advanced.open = mode === "custom" || mode === "unconfigured";
    const clear = byId(IDS.clear);
    if (clear) clear.textContent = publicModel.available ? "使用平台服务" : "清除访问密钥";
    window.dispatchEvent(new CustomEvent("zhilink:model-mode-change", {
      detail: { mode, available: publicModel.available, provider: publicModel.provider, model: publicModel.model },
    }));
  }

  function applyOverrideAvailability() {
    const allow = publicModel.userOverrideAllowed;
    [IDS.provider, IDS.apiKey, IDS.baseUrl, IDS.model, IDS.clear].forEach(id => {
      const element = byId(id);
      if (!element) return;
      element.disabled = !allow;
      if (!allow) element.title = "当前部署未开放企业自有 AI 服务设置。";
      else if (element.title === "当前部署未开放企业自有 AI 服务设置。") element.removeAttribute("title");
    });
    updateDraftState();
  }

  function ingestPublicStatus(status) {
    publicModel.available = status?.available === true;
    publicModel.provider = String(status?.provider || "");
    publicModel.model = String(status?.model || "");
    publicModel.userOverrideAllowed = status?.user_override_allowed !== false;
    publicModel.loaded = true;
    applyOverrideAvailability();
    renderModelStatus();
  }

  async function refreshPublicModelStatus() {
    try {
      const response = await fetch("/api/defaults", { headers: { Accept: "application/json" }, cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      ingestPublicStatus(payload?.public_model || {});
    } catch (error) {
      console.warn("无法读取 AI 服务状态。", error);
      ingestPublicStatus({ available: false, user_override_allowed: true });
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
    dirty = publicModel.userOverrideAllowed && !sameConfig(readDraft(), getActiveConfig());
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
    if (key) key.value = publicModel.loaded && !publicModel.userOverrideAllowed ? "" : config.api_key;
    if (baseUrl) baseUrl.value = config.base_url;
    if (model) model.value = config.model;
    if (temperature) temperature.value = String(config.temperature);
    if (byId(IDS.temperatureValue)) byId(IDS.temperatureValue).textContent = String(config.temperature);
    dirty = false;
    updateDraftState();
    renderModelStatus();
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
    if (!publicModel.userOverrideAllowed) return;
    activeConfig = cloneConfig(readDraft());
    persistActiveConfig(activeConfig);
    dirty = false;
    renderModelStatus();
    updateDraftState();
  }

  function shouldAllowClose() {
    if (!sessionOpen || !dirty) return true;
    const discard = window.confirm("AI 服务设置有未保存的修改。要放弃这些修改吗？");
    if (!discard) return false;
    restoreDraftFromActive();
    return true;
  }

  function applyProviderPreset() {
    const provider = byId(IDS.provider)?.value || "";
    const preset = providerPresets[provider];
    if (!preset) return;
    const baseUrl = byId(IDS.baseUrl);
    const model = byId(IDS.model);
    if (baseUrl) baseUrl.value = preset.base_url || "";
    if (model) model.value = preset.model || "";
    if (preset.tip && typeof toast === "function") toast(preset.tip);
  }

  async function testDraftConnection() {
    const button = byId(IDS.test);
    const result = byId(IDS.result);
    const draft = readDraft();
    const usingCustom = publicModel.userOverrideAllowed && Boolean(draft.api_key);
    if (usingCustom && (!draft.base_url || !draft.model)) {
      if (result) result.textContent = "使用企业自有 AI 服务时，请填写服务地址和模型名称后再检查。";
      return;
    }
    if (!usingCustom && publicModel.loaded && !publicModel.available) {
      if (result) result.textContent = "AI 服务尚未就绪，请配置企业自有 AI 服务后再检查。";
      return;
    }
    try {
      if (typeof setLoading === "function") setLoading(button, true, "检查中...");
      const payload = {
        api_key: usingCustom ? draft.api_key : "",
        base_url: draft.base_url,
        model: draft.model,
        temperature: draft.temperature,
      };
      const response = typeof apiPost === "function" ? await apiPost("/api/test-connection", payload) : null;
      if (!response) throw new Error("服务检查暂不可用。");
      if (result) {
        const scope = usingCustom ? "当前编辑设置，尚未保存" : "平台服务";
        result.textContent = response.ok
          ? `服务可用（${scope}）：${response.content || response.mode || "连接正常"}`
          : `服务不可用：${response.error || "请检查连接设置"}`;
      }
    } catch (error) {
      if (result) result.textContent = `服务不可用：${error.message || String(error)}`;
    } finally {
      if (typeof setLoading === "function") setLoading(button, false);
    }
  }

  function initialize(defaults) {
    providerPresets = { ...(defaults?.provider_presets || {}) };
    const provider = byId(IDS.provider);
    const fallbackProvider = providerPresets["通义千问 DashScope"] ? "通义千问 DashScope" : Object.keys(providerPresets)[0] || "";
    if (provider) {
      provider.innerHTML = Object.keys(providerPresets)
        .map(name => `<option value="${String(name).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;")}">${String(name).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")}</option>`)
        .join("");
    }

    const savedProvider = localStorage.getItem("zhilian_provider") || fallbackProvider;
    const activeProvider = providerPresets[savedProvider] ? savedProvider : fallbackProvider;
    const preset = providerPresets[activeProvider] || { base_url: "", model: "" };
    activeConfig = {
      provider: activeProvider,
      api_key: sessionStorage.getItem("zhilian_api_key") || "",
      base_url: localStorage.getItem("zhilian_base_url") || preset.base_url || "",
      model: localStorage.getItem("zhilian_model") || preset.model || "",
      temperature: Number(localStorage.getItem("zhilian_temperature") || 0.35),
    };
    initialized = true;
    restoreDraftFromActive();
    if (defaults?.public_model) ingestPublicStatus(defaults.public_model);
    else refreshPublicModelStatus();
  }

  function handleClick(event) {
    const target = event.target instanceof Element ? event.target : null;
    if (!target) return;

    if (target.closest(`#${IDS.toggle}`)) {
      event.preventDefault();
      const key = byId(IDS.apiKey);
      if (key) key.type = key.type === "password" ? "text" : "password";
      return;
    }
    if (target.closest(`#${IDS.clear}`)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (!publicModel.userOverrideAllowed) return;
      const key = byId(IDS.apiKey);
      if (key) key.value = "";
      updateDraftState();
      renderModelStatus();
      if (typeof toast === "function") toast(publicModel.available ? "已选择平台 AI 服务，保存后生效。" : "已清除访问密钥，保存后生效。");
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
      if (!dirty) return;
      commitDraft();
      if (typeof toast === "function") toast("AI 服务设置已保存。");
      byId(IDS.close)?.click();
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
    if (!panel || !(event.target instanceof Node) || !panel.contains(event.target)) return;
    if (event.type === "change" && event.target?.id === IDS.provider) applyProviderPreset();
    if (event.target?.id === IDS.temperature && byId(IDS.temperatureValue)) {
      byId(IDS.temperatureValue).textContent = String(byId(IDS.temperature)?.value || "0.35");
    }
    window.setTimeout(() => {
      updateDraftState();
      renderModelStatus();
    }, 0);
  }

  function installObserver() {
    if (observer || !document.body) return;
    let wasOpen = document.body.classList.contains("ui-v4-api-open");
    if (wasOpen) beginEditSession();
    observer = new MutationObserver(() => {
      const open = document.body.classList.contains("ui-v4-api-open");
      if (open && !wasOpen) beginEditSession();
      if (!open && wasOpen) endEditSession();
      wasOpen = open;
    });
    observer.observe(document.body, { attributes: true, attributeFilter: ["class"] });
  }

  function start() {
    if (started) return;
    started = true;
    ensureAdvancedSettings();
    document.addEventListener("click", handleClick, true);
    document.addEventListener("input", handleDraftChange, true);
    document.addEventListener("change", handleDraftChange, true);
    installObserver();
    if (initialized) {
      restoreDraftFromActive();
      renderModelStatus();
    }
    window.ZHILINK_MODEL_CONFIG_SAVE_V4_READY = true;
  }

  window.ZHILINK_MODEL_CONFIG = Object.freeze({
    initialize,
    getActiveConfig,
    getRequestConfig: getActiveRequestConfig,
    requireRequestConfig,
    renderStatus: renderModelStatus,
    isInitialized: () => initialized,
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
