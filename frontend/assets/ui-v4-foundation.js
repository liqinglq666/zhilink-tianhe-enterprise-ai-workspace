/* UI V4 foundation: native markup already loads the stylesheet at first paint. */
(() => {
  function apply() {
    if (!document.body) return;
    document.body.classList.add("ui-v4-foundation");
    document.documentElement.dataset.zhilinkUiFoundation = "v4";
    window.ZHILINK_UI_V4_FOUNDATION_READY = true;
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", apply, { once: true });
  else apply();
})();
