/* UI V4 model drawer controller for native markup. */
(() => {
  const VERSION = "20260811.1";
  let bound = false;

  function ensureStyles() {
    if (document.querySelector("link[data-api-drawer-v4]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `/assets/api-drawer-v4.css?v=${VERSION}`;
    link.dataset.apiDrawerV4 = "true";
    document.head.appendChild(link);
  }

  function syncOpenState() {
    const panel = document.getElementById("apiPanel");
    const backdrop = document.getElementById("uiV4ApiBackdrop");
    if (!panel) return;
    const open = document.body.classList.contains("ui-v4-api-open");
    panel.setAttribute("aria-hidden", String(!open));
    backdrop?.setAttribute("aria-hidden", String(!open));
    if (open && !(document.activeElement instanceof Element && panel.contains(document.activeElement))) {
      window.setTimeout(() => document.getElementById("apiKey")?.focus(), 30);
    }
  }

  function openDrawer() {
    document.body.classList.add("ui-v4-api-open");
    window.ZHILINK_UI_V4_RUNTIME?.schedule?.("api-open");
    syncOpenState();
  }

  function closeDrawer() {
    document.body.classList.remove("ui-v4-api-open");
    window.ZHILINK_UI_V4_RUNTIME?.schedule?.("api-close");
    syncOpenState();
  }

  function bindControls() {
    if (bound) return;
    bound = true;
    document.getElementById("uiV4ApiClose")?.addEventListener("click", closeDrawer);
    document.getElementById("uiV4ApiBackdrop")?.addEventListener("click", closeDrawer);
    const source = document.getElementById("openApiSettings");
    source?.addEventListener("click", event => {
      event.preventDefault();
      event.stopImmediatePropagation();
      openDrawer();
    }, true);
  }

  function start() {
    ensureStyles();
    const panel = document.getElementById("apiPanel");
    if (!panel) return;
    panel.classList.add("api-drawer-v4");
    panel.dataset.apiDrawerV4 = "true";
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-modal", "true");
    panel.setAttribute("aria-labelledby", "apiDrawerTitle");
    bindControls();
    window.ZHILINK_UI_V4_RUNTIME?.subscribe?.(syncOpenState, { immediate: false });
    syncOpenState();
    window.ZHILINK_API_DRAWER_V4_READY = true;
  }

  window.ZHILINK_API_DRAWER_V4 = { open: openDrawer, close: closeDrawer, sync: syncOpenState };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
