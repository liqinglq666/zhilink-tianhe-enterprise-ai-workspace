/* UI V4 foundation loader. No business behavior changes live in this file. */
(() => {
  const VERSION = "20260810.1";

  function ensureStyles() {
    if (document.querySelector("link[data-ui-v4-foundation]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `/assets/ui-v4-foundation.css?v=${VERSION}`;
    link.dataset.uiV4Foundation = "true";
    document.head.appendChild(link);
  }

  function apply() {
    ensureStyles();
    if (!document.body) return;
    document.body.classList.add("ui-v4-foundation");
    document.documentElement.dataset.zhilinkUiFoundation = "v4";
    window.ZHILINK_UI_V4_FOUNDATION_READY = true;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply, { once: true });
  } else {
    apply();
  }
})();
