/* Small runtime guards for the live redesign. */
(() => {
  const WORKSPACE_KEY_STORAGE = "zhilian_workspace_key_v1";
  const UI_V2_SCRIPT = "/assets/ui-v2-dashboard.js?v=20260805.1";
  const DATA_PROVENANCE_SCRIPT = "/assets/data-provenance-guard.js?v=20260806.1";
  const DATA_PROVENANCE_STYLE = "/assets/data-provenance-guard.css?v=20260806.1";
  const publicModel = {
    loaded: false,
    available: false,
    provider: "",
    model: "",
    userOverrideAllowed: true,
  };

  function ensureWorkspaceKey() {
    const current = localStorage.getItem(WORKSPACE_KEY_STORAGE) || "";
    if (current.length >= 32) return current;
    if (!window.crypto?.getRandomValues) return "";
    const bytes = new Uint8Array(32);
    window.crypto.getRandomValues(bytes);
    const key = Array.from(bytes, value => value.toString(16).padStart(2, "0")).join("");
    localStorage.setItem(WORKSPACE_KEY_STORAGE, key);
    return key;
  }

  function moveApiPanelOutsideSidebar() {
    const panel = document.getElementById("apiPanel");
    if (!panel || panel.parentElement === document.body) return;
    document.body.appendChild(panel);
  }

  function loadUiV2Dashboard() {
    if (window.ZHILINK_UI_V2_READY || document.querySelector("script[data-zhilink-ui-v2]")) return;
    const script = document.createElement("script");
    script.src = UI_V2_SCRIPT;
    script.async = false;
    script.dataset.zhilinkUiV2 = "true";
    script.addEventListener("error", () => console.error("智链天河 UI V2 加载失败，请强制刷新后重试。"), { once: true });
    document.head.appendChild(script);
  }

  function loadDataProvenanceGuard() {
    if (!document.querySelector("link[data-zhilink-data-provenance]")) {
      const style = document.createElement("link");
      style.rel = "stylesheet";
      style.href = DATA_PROVENANCE_STYLE;
      style.dataset.zhilinkDataProvenance = "true";
      document.head.appendChild(style);
    }
    if (window.ZHILINK_DATA_PROVENANCE_READY || document.querySelector("script[data-zhilink-data-provenance]")) return;
    const script = document.createElement("script");
    script.src = DATA_PROVENANCE_SCRIPT;
    script.async = false;
    script.dataset.zhilinkDataProvenance = "true";
    script.addEventListener("error", () => console.error("数据来源隔离层加载失败，请强制刷新后重试。"), { once: true });
    document.head.appendChild(script);
  }

  function hasUserApiKey() {
    const input = document.getElementById("apiKey");
    return Boolean((sessionStorage.getItem("zhilian_api_key") || input?.value || "").trim());
  }

  function currentModelMode() {
    if (hasUserApiKey()) return "custom";
    if (!publicModel.loaded) return "checking";
    return publicModel.available ? "public" : "unconfigured";
  }

  function modeCopy(mode) {
    if (mode === "custom") {
      return {
        badge: "自定义 API",
        status: "自定义 API",
        title: "当前使用用户自定义 API",
        detail: "用户 Key 仅保存在当前浏览器会话，并只发送到用户填写的兼容接口。",
      };
    }
    if (mode === "public") {
      const label = [publicModel.provider, publicModel.model].filter(Boolean).join(" · ");
      return {
        badge: "公共模型",
        status: "公共模型可用",
        title: "比赛公共模型已连接",
        detail: label ? `当前模型：${label}。API Key 留空即可直接体验。` : "API Key 留空即可直接体验比赛公共模型。",
      };
    }
    if (mode === "checking") {
      return {
        badge: "检查中",
        status: "正在检查模型",
        title: "正在确认公共模型状态",
        detail: "页面只读取不含密钥的服务端状态，不会把公共 Key 发送到浏览器。",
      };
    }
    return {
      badge: "未配置",
      status: "需配置模型",
      title: "公共模型尚未配置",
      detail: "可填写自己的 API Key、Base URL 和模型名称；比赛部署完成后也可直接使用公共模型。",
    };
  }

  function decorateApiPanel() {
    const body = document.getElementById("apiPanelBody");
    if (!body) return;

    if (!document.getElementById("publicModelModeNotice")) {
      const notice = document.createElement("div");
      notice.id = "publicModelModeNotice";
      notice.className = "public-model-mode-notice";
      notice.innerHTML = "<strong data-public-model-title></strong><span data-public-model-detail></span>";
      body.insertBefore(notice, body.firstChild);
    }

    const keyInput = document.getElementById("apiKey");
    if (keyInput) keyInput.placeholder = "可选：留空使用比赛公共模型，或填写自己的 sk-...";

    Array.from(body.querySelectorAll("label")).forEach(label => {
      const text = label.childNodes[0]?.textContent?.trim();
      if (text === "API Key") label.childNodes[0].textContent = "API Key（可选）";
    });

    const test = document.getElementById("testConnection");
    if (test) test.textContent = "测试当前模型";

    if (!document.getElementById("customApiHelp")) {
      const help = document.createElement("p");
      help.id = "customApiHelp";
      help.className = "custom-api-help";
      help.textContent = "Base URL 和模型名称仅在填写自有 API Key 时生效；公共 Key 永远不会发送到用户指定的地址。";
      const result = document.getElementById("connectionResult");
      body.insertBefore(help, result || null);
    }
  }

  function applyOverrideAvailability() {
    const allow = publicModel.userOverrideAllowed;
    const fields = ["apiKey", "baseUrl", "modelName", "providerSelect", "clearKey"];
    fields.forEach(id => {
      const element = document.getElementById(id);
      if (!element) return;
      element.disabled = !allow;
      if (!allow) element.title = "当前比赛部署未开放用户自定义 API。";
      else if (element.title === "当前比赛部署未开放用户自定义 API。") element.removeAttribute("title");
    });
  }

  async function refreshPublicModelStatus() {
    try {
      const response = await fetch("/api/defaults", { headers: { Accept: "application/json" }, cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      const status = payload?.public_model || {};
      publicModel.available = status.available === true;
      publicModel.provider = String(status.provider || "");
      publicModel.model = String(status.model || "");
      publicModel.userOverrideAllowed = status.user_override_allowed !== false;
    } catch (error) {
      console.warn("无法读取公共模型状态。", error);
      publicModel.available = false;
      publicModel.provider = "";
      publicModel.model = "";
      publicModel.userOverrideAllowed = true;
    } finally {
      publicModel.loaded = true;
      applyOverrideAvailability();
      if (typeof window.updateModeBadge === "function") window.updateModeBadge();
    }
  }

  function installPublicModelMode() {
    if (window.__ZHILINK_PUBLIC_MODEL_MODE_INSTALLED) return;
    if (typeof window.getConfig !== "function" || typeof window.updateModeBadge !== "function") {
      window.setTimeout(installPublicModelMode, 50);
      return;
    }
    window.__ZHILINK_PUBLIC_MODEL_MODE_INSTALLED = true;

    const originalGetConfig = window.getConfig;
    window.getConfig = function publicAwareGetConfig() {
      const config = originalGetConfig();
      return {
        ...config,
        api_key: String(config.api_key || "").trim(),
      };
    };

    window.requireApiConfig = function publicAwareRequireApiConfig() {
      const config = window.getConfig();
      if (config.api_key && (!String(config.base_url || "").trim() || !String(config.model || "").trim())) {
        throw new Error("使用自定义 API 时，请完整填写 API Key、Base URL 和模型名称。 ");
      }
      if (!config.api_key && publicModel.loaded && !publicModel.available) {
        throw new Error("比赛公共模型尚未配置，请填写自己的 API Key 后再生成。 ");
      }
      return config;
    };

    window.updateModeBadge = function publicAwareModeBadge() {
      const mode = currentModelMode();
      const copy = modeCopy(mode);
      const badge = document.getElementById("modeBadge");
      const homeStatus = document.getElementById("homeApiStatus");
      const topStatus = document.getElementById("topApiStatus");
      const clear = document.getElementById("clearKey");
      document.body.dataset.modelMode = mode;

      if (badge) {
        badge.textContent = copy.badge;
        badge.className = mode === "unconfigured" ? "status-badge local" : "status-badge ai";
      }
      if (homeStatus) homeStatus.textContent = copy.badge;
      if (topStatus) {
        topStatus.textContent = copy.status;
        topStatus.className = mode === "unconfigured" ? "top-status pending" : "top-status ready";
      }
      if (clear) clear.textContent = publicModel.available ? "恢复公共模型" : "清空自定义 API";

      const notice = document.getElementById("publicModelModeNotice");
      if (notice) {
        notice.dataset.mode = mode;
        const title = notice.querySelector("[data-public-model-title]");
        const detail = notice.querySelector("[data-public-model-detail]");
        if (title) title.textContent = copy.title;
        if (detail) detail.textContent = copy.detail;
      }

      window.dispatchEvent(new CustomEvent("zhilink:model-mode-change", {
        detail: {
          mode,
          available: publicModel.available,
          provider: publicModel.provider,
          model: publicModel.model,
        },
      }));
    };

    decorateApiPanel();
    window.updateModeBadge();
    refreshPublicModelStatus();

    const keyInput = document.getElementById("apiKey");
    keyInput?.addEventListener("input", () => window.updateModeBadge());
    window.addEventListener("storage", event => {
      if (event.key === "zhilian_api_key") window.updateModeBadge();
    });
  }

  function injectPublicModelStyles() {
    if (document.getElementById("publicModelModeStyles")) return;
    const style = document.createElement("style");
    style.id = "publicModelModeStyles";
    style.textContent = `
      .public-model-mode-notice{display:grid;gap:4px;padding:12px 14px;margin-bottom:12px;border:1px solid #bfdbfe;border-radius:12px;background:linear-gradient(135deg,#eff6ff,#f0fdfa);color:#1e3a8a;line-height:1.55}
      .public-model-mode-notice strong{font-size:13px;color:#1d4ed8}
      .public-model-mode-notice span{font-size:12px;color:#475569}
      .public-model-mode-notice[data-mode="custom"]{border-color:#c4b5fd;background:linear-gradient(135deg,#f5f3ff,#eff6ff)}
      .public-model-mode-notice[data-mode="unconfigured"]{border-color:#fed7aa;background:#fff7ed}
      .public-model-mode-notice[data-mode="unconfigured"] strong{color:#c2410c}
      .public-model-mode-notice[data-mode="checking"]{border-color:#e2e8f0;background:#f8fafc}
      .custom-api-help{margin:8px 0 2px;font-size:11px;line-height:1.5;color:#64748b}
      body[data-model-mode="public"] #topApiStatus{background:#ecfdf5;color:#047857;border-color:#a7f3d0}
      body[data-model-mode="custom"] #topApiStatus{background:#f5f3ff;color:#6d28d9;border-color:#ddd6fe}
      body[data-model-mode="checking"] #topApiStatus{background:#f8fafc;color:#475569;border-color:#e2e8f0}
    `;
    document.head.appendChild(style);
  }

  ensureWorkspaceKey();
  const apply = () => {
    ensureWorkspaceKey();
    moveApiPanelOutsideSidebar();
    injectPublicModelStyles();
    installPublicModelMode();
    loadUiV2Dashboard();
    loadDataProvenanceGuard();
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", apply, { once: true });
  else window.setTimeout(apply, 0);
  window.addEventListener("resize", moveApiPanelOutsideSidebar, { passive: true });

  window.ZHILINK_UI_REDESIGN_LIVE_FIXES_READY = true;
})();
