/* UI V4 foundation loader. No business behavior changes live in this file. */
(() => {
  const VERSION = "20260810.2";
  const EARLY_STYLE_ASSETS = [
    ["ui-v4-foundation.css", "20260810.2"],
    ["ui-v4-dashboard.css", "20260810.1"],
    ["ui-v4-workspace.css", "20260810.1"],
    ["ui-v4-navigation.css", "20260810.1"],
    ["ui-v4-overlays.css", "20260810.2"],
    ["ui-v4-states.css", "20260810.1"],
    ["ui-v4-forms.css", "20260810.1"],
    ["ui-v4-results.css", "20260810.1"],
    ["ui-v4-final-qa.css", "20260810.1"],
    ["model-config-save-v4.css", "20260810.1"],
  ];

  function preloadStyles() {
    if (!document.head) return;
    EARLY_STYLE_ASSETS.forEach(([filename, version]) => {
      const href = `/assets/${filename}?v=${version}`;
      if (document.querySelector(`link[rel="preload"][href="${href}"]`)) return;
      const link = document.createElement("link");
      link.rel = "preload";
      link.as = "style";
      link.href = href;
      link.dataset.uiV4Preload = filename;
      document.head.appendChild(link);
    });
  }

  function ensureStyles() {
    if (document.querySelector("link[data-ui-v4-foundation]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `/assets/ui-v4-foundation.css?v=${VERSION}`;
    link.dataset.uiV4Foundation = "true";
    document.head.appendChild(link);
  }

  function removeLegacyDecorations() {
    document.querySelectorAll(".live-ai-orbit").forEach(node => node.remove());
  }

  function apply() {
    ensureStyles();
    if (!document.body) return;
    document.body.classList.add("ui-v4-foundation");
    removeLegacyDecorations();
    document.documentElement.dataset.zhilinkUiFoundation = "v4";
    window.ZHILINK_UI_V4_FOUNDATION_READY = true;
  }

  preloadStyles();

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", apply, { once: true });
  } else {
    apply();
  }
})();