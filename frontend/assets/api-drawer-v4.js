/* UI V4 model drawer controller for native markup. */
(() => {
  let bound = false;

  function syncOpenState() {
    const panel = document.getElementById("apiPanel");
    const backdrop = document.getElementById("uiV4ApiBackdrop");
    if (!panel) return;
    const open = document.body.classList.contains("ui-v4-api-open");
    panel.setAttribute("aria-hidden", String(!open));
    backdrop?.setAttribute("aria-hidden", String(!open));
    if (open && !(document.activeElement instanceof Element && panel.contains(document.activeElement))) {
      window.setTimeout(() => {
        const target = document.getElementById("modelConfigAdvancedSettingsSummary") || document.getElementById("apiKey");
        target?.focus();
      }, 30);
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
    if (!document.getElementById("apiPanel")) return;
    bindControls();
    window.ZHILINK_UI_V4_RUNTIME?.subscribe?.(syncOpenState, { immediate: false });
    syncOpenState();
    window.ZHILINK_API_DRAWER_V4_READY = true;
  }

  window.ZHILINK_API_DRAWER_V4 = { open: openDrawer, close: closeDrawer, sync: syncOpenState };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
