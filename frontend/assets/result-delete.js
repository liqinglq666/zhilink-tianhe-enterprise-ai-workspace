/* Per-result deletion for generated workspace materials. */
(() => {
  const contracts = window.ZHILINK_WORKSPACE_CONTRACTS;
  const RESULT_SUFFIX = "Result";
  const STYLE_ID = "zhilink-result-delete-style";

  function moduleKeyFromPanel(panel) {
    const id = String(panel?.id || "");
    return id.endsWith(RESULT_SUFFIX) ? id.slice(0, -RESULT_SUFFIX.length) : "";
  }

  function installStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      .result-actions .delete-result {
        color: var(--danger, #b42318);
        border-color: color-mix(in srgb, var(--danger, #b42318) 24%, transparent);
        background: color-mix(in srgb, var(--danger, #b42318) 5%, transparent);
      }
      @media (hover: hover) and (pointer: fine) {
        .result-actions .delete-result:hover {
          border-color: color-mix(in srgb, var(--danger, #b42318) 42%, transparent);
          background: color-mix(in srgb, var(--danger, #b42318) 9%, transparent);
        }
      }
    `;
    document.head.appendChild(style);
  }

  function decoratePanel(panel) {
    if (!(panel instanceof HTMLElement) || panel.classList.contains("empty")) return;
    const actions = panel.querySelector(".result-actions");
    if (!(actions instanceof HTMLElement) || actions.querySelector(".delete-result")) return;
    const key = moduleKeyFromPanel(panel);
    if (!key || !state?.results?.[key]) return;

    const button = document.createElement("button");
    button.type = "button";
    button.className = "inline-action delete-result";
    button.dataset.key = key;
    button.textContent = "删除";
    button.setAttribute("aria-label", `删除${resultTitles?.[key] || "当前"}生成结果`);
    button.setAttribute("title", "删除当前生成结果");
    actions.appendChild(button);
  }

  function decorateAll() {
    document.querySelectorAll(".result-panel").forEach(decoratePanel);
  }

  function persistResultState() {
    sessionStorage.setItem("zhilian_results", JSON.stringify(state.results || {}));
    sessionStorage.setItem("zhilian_meta", JSON.stringify(state.meta || {}));
  }

  function removeResult(key) {
    const normalizedKey = String(key || "").trim();
    if (!normalizedKey || !state?.results?.[normalizedKey]) return false;
    const title = resultTitles?.[normalizedKey] || "当前结果";
    const accepted = window.confirm(
      `确认删除“${title}”的当前生成结果吗？\n\n此操作不会清空该模块的输入内容。若当前工作区已保存为项目，请再次保存项目以记录本次删除。`,
    );
    if (!accepted) return false;

    delete state.results[normalizedKey];
    delete state.meta[normalizedKey];
    persistResultState();
    showResult(normalizedKey, {}, "commit");
    updateProgress();
    if (typeof toast === "function") toast(`已删除${title}生成结果`);
    return true;
  }

  function bindActions() {
    document.addEventListener("click", event => {
      const button = event.target.closest?.(".delete-result");
      if (!button) return;
      event.preventDefault();
      removeResult(button.dataset.key);
    });
  }

  function start() {
    installStyle();
    bindActions();
    decorateAll();
    const resultUpdatedEvent = contracts?.events?.resultUpdated;
    if (resultUpdatedEvent) {
      window.addEventListener(resultUpdatedEvent, () => queueMicrotask(decorateAll));
    }
    window.ZHILINK_RESULT_DELETE_READY = true;
  }

  window.ZHILINK_RESULT_DELETE = Object.freeze({
    removeResult,
    refresh: decorateAll,
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
