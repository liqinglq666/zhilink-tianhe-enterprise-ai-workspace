/* Recover known workspace JSON keys and load shared feature styles before feature modules start. */
(() => {
  const FEATURE_STYLES_URL = "/assets/feature-styles.css?v=20260824.1";

  function ensureFeatureStyles() {
    if (document.querySelector("link[data-zhilink-feature-styles]")) return;
    const stylesheet = document.createElement("link");
    stylesheet.rel = "stylesheet";
    stylesheet.href = FEATURE_STYLES_URL;
    stylesheet.dataset.zhilinkFeatureStyles = "true";

    // Compatibility markers keep legacy feature loaders dormant until their dead code is removed.
    stylesheet.dataset.generationControls = "true";
    stylesheet.dataset.accountAccess = "true";
    stylesheet.dataset.projectStorage = "true";
    stylesheet.dataset.projectHistory = "true";
    stylesheet.dataset.reviewWorkflow = "true";
    stylesheet.dataset.structuredResults = "true";
    stylesheet.dataset.policySources = "true";
    stylesheet.dataset.knowledgeBase = "true";
    stylesheet.dataset.serviceWorkflow = "true";
    stylesheet.dataset.zhilinkDataProvenance = "true";
    document.head.appendChild(stylesheet);
  }

  ensureFeatureStyles();

  const targets = [
    [localStorage, "zhilian_identity"],
    [localStorage, "zhilian_current_project_v1"],
    [sessionStorage, "zhilian_profile"],
    [sessionStorage, "zhilian_form_inputs"],
    [sessionStorage, "zhilian_results"],
    [sessionStorage, "zhilian_meta"],
  ];
  const recovered = [];

  for (const [storage, key] of targets) {
    const raw = storage.getItem(key);
    if (!raw) continue;
    try {
      JSON.parse(raw);
    } catch (_) {
      storage.removeItem(key);
      recovered.push(key);
    }
  }

  window.ZHILINK_FEATURE_STYLES_READY = true;
  window.ZHILINK_STORAGE_RECOVERY = Object.freeze({ recovered: Object.freeze(recovered) });
  if (recovered.length) console.warn("Recovered invalid workspace storage", recovered);
})();
