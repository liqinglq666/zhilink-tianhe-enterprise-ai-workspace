/* UI V4 model config: draft -> test -> explicit save, with server-side public model support. */
(() => {
  const VERSION = "20260810.3";
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
    close: "uiV4ApiClose",
    backdrop: "uiV4ApiBackdrop",
    result: "connectionResult",
  };
  const originalSaveConfig = typeof window.saveConfig === "function" ? window.saveConfig : null;
  let activeConfig = null;
  let sessionOpen = false;
  let dirty = false;
  let observer = null;
  const publicModel = {
    loaded: false,
    available: false,
    provider: "",
    model: "",
    userOverrideAllowed: true,
  };

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
      api_key: publicModel.loaded && !publicModel.userOverrideAllowed ? "" : config.api_key,
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
  function modelMode(config = getActiveConfig()) {
    if (publicModel.loaded && !publicModel.userOverrideAllowed) return publicModel.available ? "public" : "unconfigured";
    if (String(config.api_key || "").trim()) return "custom";
    if (!publicModel.loaded) return "checking";
    return publicModel.available ? "public" : "unconfigured";
  }
  function modeCopy(mode) {
    if (mode === "custom") return {
      badge: "自定义 API",
      top: "自定义 API",
      title: "当前使用自定义 API",
      detail: "API Key 仅保存在当前浏览器会话，并发送到你保存的兼容接口。",
    };
    if (mode === "public") {
      const detail = [publicModel.provider, publicModel.model].filter(Boolean).join(" · ");
      return {
        badge: "公共模型",
        top: "公共模型可用",
        title: "公共模型已连接",
        detail: detail ? `当前部署模型：${detail}。无需在浏览器保存公共 Key。` : "当前部署已提供公共模型，无需填写 API Key。",
      };
    }
    if (mode === "checking") return {
      badge: "检查中",
      top: "正在检查模型",
      title: "正在确认模型状态",
      detail: "仅读取不包含密钥的服务端状态。",
    };
    return {
      badge: "待配置",
      top: "需配置模型",
      title: "当前没有可用模型",
      detail: "部署方尚未提供公共模型，请保存自己的 API Key、Base URL 和模型名称。",
    };
  }

  function ensurePublicNotice() {
    const body = byId("apiPanelBody");
    const fields = body?.querySelector(".api-drawer-fields");
    if (!body || !fields) return null;
    let notice = byId("publicModelModeNotice");
    if (!notice) {
      notice = document.createElement("div");
      notice.id = "publicModelModeNotice";
      notice.className = "public-model-mode-notice";
      notice.innerHTML = "<strong data-public-model-title></strong><span data-public-model-detail></span>";
      body.insertBefore(notice, fields);
    }
    return notice;
  }

  function renderModelStatus() {
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
    const clear = byId(IDS.clear);
    if (clear) clear.textContent = publicModel.available ? "恢复公共模型" : "清空 API Key";
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
      if (!allow) element.title = "当前部署未开放用户自定义 API。";
      else if (element.title === "当前部署未开放用户自定义 API。") element.removeAttribute("title");
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
      const fromState = typeof state !== "undefined" ? state.defaults?.public_model : null;
      if (fromState) {
        ingestPublicStatus(fromState);
        return;
      }
      const response = await fetch("/api/defaults", { headers: { Accept: "application/json" }, cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      ingestPublicStatus(payload?.public_model || {});
    } catch (error) {
      console.warn("无法读取公共模型状态。", error);
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
    if (originalSaveConfig) originalSaveConfig();
    dirty = false;
    renderModelStatus();
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
    const usingCustom = publicModel.userOverrideAllowed && Boolean(draft.api_key);
    if (usingCustom && (!draft.base_url || !draft.model)) {
      if (result) result.textContent = "使用自定义 API 时，请填写 Base URL 和模型名称后再测试。";
      return;
    }
    if (!usingCustom && publicModel.loaded && !publicModel.available) {
      if (result) result.textContent = "当前没有可用公共模型，请填写并保存自己的 API 配置。";
      return;
    }
    try {
      if (typeof setLoading === "function") setLoading(button, true, "测试中...");
      const payload = {
        api_key: usingCustom ? draft.api_key : "",
        base_url: draft.base_url,
        model: draft.model,
        temperature: draft.temperature,
      };
      const response = typeof apiPost === "function" ? await apiPost("/api/test-connection", payload) : null;
      if (!response) throw new Error("连接测试不可用。");
      if (result) {
        const scope = usingCustom ? "当前编辑内容，尚未保存" : "公共模型";
        result.textContent = response.ok
          ? `连接成功（${scope}）：${response.content || response.mode || "模型可用"}`
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
    window.updateModeBadge = renderModelStatus;
    window.requireApiConfig = function requireAvailableModel() {
      const config = getActiveRequestConfig();
      if (config.api_key) {
        if (!config.base_url || !config.model) throw new Error("使用自定义 API 时，请完整保存 API Key、Base URL 和模型名称。 ");
        return config;
      }
      if (publicModel.loaded && !publicModel.available) {
        throw new Error("当前公共模型尚未配置，请打开“模型配置”并保存自己的 API 后再生成。 ");
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
      if (!publicModel.userOverrideAllowed) return;
      const key = byId(IDS.apiKey);
      if (key) key.value = "";
      updateDraftState();
      renderModelStatus();
      if (typeof toast === "function") toast(publicModel.available ? "已切换当前编辑内容为公共模型，保存后生效。" : "已从当前编辑内容中清空 API Key，保存后生效。");
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
      if (typeof toast === "function") toast("模型配置已保存。 ");
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
    if (!sessionOpen || !panel || !(event.target instanceof Node) || !panel.contains(event.target)) return;
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
    ensureStyles();
    installCompatibilityOverrides();
    document.addEventListener("click", handleClick, true);
    document.addEventListener("input", handleDraftChange, true);
    document.addEventListener("change", handleDraftChange, true);
    installObserver();
    window.setTimeout(() => {
      if (!activeConfig && byId(IDS.provider)?.options?.length) captureActiveFromStorage();
      renderModelStatus();
      refreshPublicModelStatus();
    }, 0);
    window.ZHILINK_MODEL_CONFIG_SAVE_V4_READY = true;
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
