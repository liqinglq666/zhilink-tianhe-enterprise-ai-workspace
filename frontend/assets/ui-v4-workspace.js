/* UI V4 workspace: focused input/result workbench for business modules. */
(() => {
  const contracts = window.ZHILINK_WORKSPACE_CONTRACTS;
  const ICONS = window.ZHILINK_UI_V4_ICONS;
  if (!contracts || !ICONS) throw new Error("Workspace runtime and icons must load before workspace.");

  const SHARED_MODULES = contracts.modules;

  function moduleMeta(id) {
    if (id === "report") return ["汇总已有结果", "支持多格式导出", "不导出 API Key"];
    if (id === "profile") return ["可选上下文", "支持快速示例", "结果可归档"];
    return ["AI 辅助生成", "人工复核后使用", "结果可归档"];
  }

  function decoratePage(page) {
    const id = page.id;
    const shared = SHARED_MODULES[id];
    const input = page.querySelector(":scope > .content-card");
    const result = page.querySelector(":scope > .result-panel");
    if (!shared || !input || !result) return;

    const head = input.querySelector(".section-head");
    const iconHolder = head?.querySelector(":scope > span");
    if (iconHolder && iconHolder.dataset.uiV4Icon !== "true") {
      iconHolder.innerHTML = ICONS[shared.icon] || ICONS.home;
      iconHolder.dataset.uiV4Icon = "true";
      iconHolder.setAttribute("aria-hidden", "true");
    }

    if (head && !input.querySelector(".ui-v4-module-meta")) {
      const meta = document.createElement("div");
      meta.className = "ui-v4-module-meta";
      moduleMeta(id).forEach(label => {
        const item = document.createElement("span");
        item.textContent = label;
        meta.appendChild(item);
      });
      head.insertAdjacentElement("afterend", meta);
    }

    input.querySelectorAll("textarea").forEach(textarea => textarea.setAttribute("spellcheck", "false"));
    input.querySelectorAll(".sticky-actions button.primary").forEach(button => {
      if (button.dataset.uiV4Arrow === "true") return;
      button.insertAdjacentHTML("beforeend", ICONS.arrow);
      button.dataset.uiV4Arrow = "true";
    });
  }

  function apply() {
    if (!document.body) return;
    document.documentElement.dataset.zhilinkWorkspace = "v4";
    document.querySelectorAll(".ui-v4-business-page[id]").forEach(decoratePage);
    window.ZHILINK_UI_V4_WORKSPACE_READY = true;
  }

  function start() {
    apply();
    const runtime = window.ZHILINK_UI_V4_RUNTIME;
    if (runtime?.subscribe) runtime.subscribe(apply, { immediate: false });
    else window.addEventListener(contracts.events.workspaceStateChange, apply);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
