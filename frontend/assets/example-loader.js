/* Load non-production workspace examples only when they are actually needed. */
(() => {
  if (window.ZHILINK_EXAMPLE_LOADER_READY) return;

  const contracts = window.ZHILINK_WORKSPACE_CONTRACTS;
  if (!contracts) throw new Error("Workspace contracts must load before example data.");

  const EXAMPLES_URL = "/assets/examples.json?v=20260811.1";
  const CONTEXT_STORAGE = contracts.storage.exampleContexts;
  let loadPromise = null;

  function hasLoadedExamples() {
    return typeof exampleScenarios !== "undefined" && Object.keys(exampleScenarios).length > 0;
  }

  function hasExampleContext() {
    try {
      const value = JSON.parse(sessionStorage.getItem(CONTEXT_STORAGE) || "{}");
      return Boolean(value && typeof value === "object" && Object.keys(value).length);
    } catch (_) {
      return false;
    }
  }

  async function ensureLoaded() {
    if (hasLoadedExamples()) return exampleScenarios;
    if (!loadPromise) {
      loadPromise = fetch(EXAMPLES_URL, { cache: "force-cache" })
        .then(response => {
          if (!response.ok) throw new Error("示例数据加载失败，请稍后重试。");
          return response.json();
        })
        .then(data => {
          if (!data || typeof data !== "object" || Array.isArray(data)) {
            throw new Error("示例数据格式无效，请刷新后重试。");
          }
          Object.assign(exampleScenarios, data);
          window.ZHILINK_EXAMPLE_SCENARIOS = exampleScenarios;
          return exampleScenarios;
        })
        .catch(error => {
          loadPromise = null;
          throw error;
        });
    }
    return loadPromise;
  }

  document.addEventListener("click", event => {
    const button = event.target.closest?.(".quick-fill-btn[data-example]");
    if (!button || hasLoadedExamples()) return;

    event.preventDefault();
    event.stopPropagation();
    const exampleKey = button.dataset.example || "";
    button.disabled = true;
    button.setAttribute("aria-busy", "true");

    ensureLoaded()
      .then(() => applyExample(exampleKey))
      .catch(error => {
        if (typeof toast === "function") toast(error.message || "示例数据加载失败，请稍后重试。");
        else console.error(error);
      })
      .finally(() => {
        button.disabled = false;
        button.removeAttribute("aria-busy");
      });
  }, true);

  if (hasExampleContext()) {
    ensureLoaded().catch(error => console.warn("Example context restore skipped", error));
  }

  window.ZHILINK_EXAMPLE_LOADER = { ensureLoaded };
  window.ZHILINK_EXAMPLE_LOADER_READY = true;
})();
