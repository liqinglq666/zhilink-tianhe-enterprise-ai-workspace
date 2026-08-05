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

  ensureWorkspaceKey();
  const apply = () => {
    ensureWorkspaceKey();
    moveApiPanelOutsideSidebar();
    loadUiV2Dashboard();
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", apply, { once: true });
  else window.setTimeout(apply, 0);
  window.addEventListener("resize", moveApiPanelOutsideSidebar, { passive: true });

  window.ZHILINK_UI_REDESIGN_LIVE_FIXES_READY = true;
})();
