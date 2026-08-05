/* Small runtime guards for the live redesign. */
(() => {
  const WORKSPACE_KEY_STORAGE = "zhilian_workspace_key_v1";
  const UI_V2_SCRIPT = "/assets/ui-v2-dashboard.js?v=20260805.1";

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

  function hasUserApiKey() {
    const input = document.getElementById("apiKey");
    return Boolean((sessionStorage.getItem("zhilian_api_key") || input?.value || "").trim());
  }

  function decorateApiPanel() {
    const body = document.getElementById("apiPanelBody");
    if (!body) return;

    if (!document.getElementById("publicModelModeNotice")) {
      const notice = document.createElement("div");
      notice.id = "publicModelModeNotice";
      notice.className = "public-model-mode-notice";
      notice.innerHTML = `
        <strong>比赛公共模型已支持</strong>
        <span>API Key 留空即可使用服务端公共模型；填写自己的 Key 后，仅在当前浏览器会话中覆盖公共模型。</span>`;
      body.insertBefore(notice, body.firstChild);
    }

    const keyInput = document.getElementById("apiKey");
    if (keyInput) keyInput.placeholder = "可选：留空使用比赛公共模型，或填写自己的 sk-...";

    Array.from(body.querySelectorAll("label")).forEach(label => {
      const text = label.childNodes[0]?.textContent?.trim();
      if (text === "API Key") label.childNodes[0].textContent = "API Key（可选）";
    });

    const clear = document.getElementById("clearKey");
    if (clear) clear.textContent = "恢复公共模型";
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
      return config;
    };

    window.updateModeBadge = function publicAwareModeBadge() {
      const custom = hasUserApiKey();
      const badge = document.getElementById("modeBadge");
      const homeStatus = document.getElementById("homeApiStatus");
      const topStatus = document.getElementById("topApiStatus");
      document.body.dataset.modelMode = custom ? "custom" : "public";

      if (badge) {
        badge.textContent = custom ? "自定义 API" : "公共模型";
        badge.className = "status-badge ai";
      }
      if (homeStatus) homeStatus.textContent = custom ? "自定义 API" : "公共模型";
      if (topStatus) {
        topStatus.textContent = custom ? "自定义 API" : "公共模型可用";
        topStatus.className = "top-status ready";
      }

      const notice = document.getElementById("publicModelModeNotice");
      if (notice) notice.dataset.mode = custom ? "custom" : "public";
      window.dispatchEvent(new CustomEvent("zhilink:model-mode-change", { detail: { mode: custom ? "custom" : "public" } }));
    };

    decorateApiPanel();
    window.updateModeBadge();

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
      .public-model-mode-notice[data-mode="custom"] strong::after{content:" · 当前使用自定义 API";color:#6d28d9}
      .custom-api-help{margin:8px 0 2px;font-size:11px;line-height:1.5;color:#64748b}
      body[data-model-mode="public"] #topApiStatus{background:#ecfdf5;color:#047857;border-color:#a7f3d0}
      body[data-model-mode="custom"] #topApiStatus{background:#f5f3ff;color:#6d28d9;border-color:#ddd6fe}
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
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", apply, { once: true });
  else window.setTimeout(apply, 0);
  window.addEventListener("resize", moveApiPanelOutsideSidebar, { passive: true });

  window.ZHILINK_UI_REDESIGN_LIVE_FIXES_READY = true;
})();
