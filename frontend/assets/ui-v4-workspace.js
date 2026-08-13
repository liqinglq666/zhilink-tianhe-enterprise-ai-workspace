/* UI V4 workspace: focused input/result workbench for business modules. */
(() => {
  const contracts = window.ZHILINK_WORKSPACE_CONTRACTS;
  const ICONS = window.ZHILINK_UI_V4_ICONS;
  if (!contracts || !ICONS) throw new Error("Workspace runtime and icons must load before workspace.");

  const SHARED_MODULES = contracts.modules;
  const WORKSPACE_INPUT_LABELS = {
    profile: "企业资料",
    meeting: "会议记录",
    contract: "合同条款",
    policy: "政策需求",
    match: "供需信息",
    landing: "实施条件",
    report: "归档与导出",
  };

  function moduleMeta(id) {
    if (id === "report") return ["汇总已有结果", "支持多格式导出", "不导出 API Key"];
    if (id === "profile") return ["可选上下文", "支持快速示例", "结果可归档"];
    return ["AI 辅助生成", "人工复核后使用", "结果可归档"];
  }

  function decoratePage(id, inputLabel) {
    const shared = SHARED_MODULES[id];
    const page = document.getElementById(id);
    const input = page?.querySelector(":scope > .content-card");
    const result = page?.querySelector(":scope > .result-panel");
    if (!shared || !page || !input || !result) return;

    input.setAttribute("aria-label", `${inputLabel}输入工作区`);
    result.setAttribute("aria-label", shared.resultLabel);

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
    Object.entries(WORKSPACE_INPUT_LABELS).forEach(([id, inputLabel]) => decoratePage(id, inputLabel));
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
