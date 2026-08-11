/* UI V4 workspace: focused input/result workbench for business modules. */
(() => {
  const VERSION = "20260811.2";
  const contracts = window.ZHILINK_WORKSPACE_CONTRACTS;
  const ICONS = window.ZHILINK_UI_V4_ICONS;
  if (!contracts || !ICONS) throw new Error("Workspace runtime and icons must load before workspace.");

  const MODULES = {
    profile: { input: "企业资料", emptyTitle: "企业档案将在这里生成", emptyCopy: "填写企业资料后生成档案；结果可继续用于其他业务模块。", resultLabel: "企业档案 · 生成结果", icon: "profile" },
    meeting: { input: "会议记录", emptyTitle: "会议纪要将在这里生成", emptyCopy: "粘贴会议记录或录音转写文本，然后点击“生成会议纪要”。", resultLabel: "会议纪要 · AI 生成结果", icon: "meeting" },
    contract: { input: "合同条款", emptyTitle: "合同风险提示将在这里生成", emptyCopy: "粘贴需要审阅的关键条款，然后点击“生成风险提示”。", resultLabel: "合同风险 · AI 审阅结果", icon: "contract" },
    policy: { input: "政策需求", emptyTitle: "政策建议将在这里生成", emptyCopy: "填写政策需求或企业档案，然后点击“生成政策建议”。", resultLabel: "政策方向 · AI 建议结果", icon: "policy" },
    match: { input: "供需信息", emptyTitle: "供需协作方案将在这里生成", emptyCopy: "补充供给、需求、目标对象或业务场景中的至少一项。", resultLabel: "供需协作 · AI 方案结果", icon: "match" },
    landing: { input: "实施条件", emptyTitle: "实施计划将在这里生成", emptyCopy: "补充试点场景、角色、数据范围与复核机制后生成执行计划。", resultLabel: "实施计划 · AI 生成结果", icon: "plan" },
    report: { input: "归档与导出", emptyTitle: "运营报告将在这里生成", emptyCopy: "先完成至少一个业务模块，再整合或导出当前已有材料。", resultLabel: "运营报告 · 汇总与导出", icon: "report" },
  };

  function ensureStyles() {
    if (document.querySelector("link[data-ui-v4-workspace]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `/assets/ui-v4-workspace.css?v=${VERSION}`;
    link.dataset.uiV4Workspace = "true";
    document.head.appendChild(link);
  }

  function moduleMeta(id) {
    if (id === "report") return ["汇总已有结果", "支持多格式导出", "不导出 API Key"];
    if (id === "profile") return ["可选上下文", "支持快速示例", "结果可归档"];
    return ["AI 辅助生成", "人工复核后使用", "结果可归档"];
  }

  function decoratePage(id, config) {
    const page = document.getElementById(id);
    const input = page?.querySelector(":scope > .content-card");
    const result = page?.querySelector(":scope > .result-panel");
    if (!page || !input || !result) return;

    page.classList.add("ui-v4-workspace-page", "ui-v4-business-page");
    page.dataset.uiV4Module = id;
    input.classList.add("ui-v4-input-pane");
    result.classList.add("ui-v4-result-pane");
    input.dataset.uiV4PaneLabel = config.input;
    result.dataset.uiV4EmptyTitle = config.emptyTitle;
    result.dataset.uiV4EmptyCopy = config.emptyCopy;
    result.dataset.uiV4ResultState = result.classList.contains("empty") ? "empty" : "ready";
    input.setAttribute("aria-label", `${config.input}输入工作区`);
    result.setAttribute("aria-label", config.resultLabel);

    const head = input.querySelector(".section-head");
    const iconHolder = head?.querySelector(":scope > span");
    if (iconHolder && iconHolder.dataset.uiV4Icon !== "true") {
      iconHolder.innerHTML = ICONS[config.icon] || ICONS.home;
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
    ensureStyles();
    if (!document.body) return;
    document.body.classList.add("ui-v4-workspace");
    document.documentElement.dataset.zhilinkWorkspace = "v4";
    Object.entries(MODULES).forEach(([id, config]) => decoratePage(id, config));
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
