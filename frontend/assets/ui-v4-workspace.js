/* UI V4 workspace: focused input/result workbench for business modules. */
(() => {
  const VERSION = "20260810.3";
  const MODULES = {
    profile: { input: "企业资料", emptyTitle: "企业档案将在这里生成", emptyCopy: "填写企业资料后生成档案；结果可继续用于其他业务模块。" },
    meeting: { input: "会议记录", emptyTitle: "会议纪要将在这里生成", emptyCopy: "粘贴会议记录或录音转写文本，然后点击“生成会议纪要”。" },
    contract: { input: "合同条款", emptyTitle: "合同风险提示将在这里生成", emptyCopy: "粘贴需要审阅的关键条款，然后点击“生成风险提示”。" },
    policy: { input: "政策需求", emptyTitle: "政策建议将在这里生成", emptyCopy: "填写政策需求或企业档案，然后点击“生成政策建议”。" },
    match: { input: "供需信息", emptyTitle: "供需协作方案将在这里生成", emptyCopy: "补充供给、需求、目标对象或业务场景中的至少一项。" },
    landing: { input: "实施条件", emptyTitle: "实施计划将在这里生成", emptyCopy: "补充试点场景、角色、数据范围与复核机制后生成执行计划。" },
    report: { input: "归档与导出", emptyTitle: "运营报告将在这里生成", emptyCopy: "先完成至少一个业务模块，再整合或导出当前已有材料。" },
  };
  let observer = null;
  let queued = false;

  function ensureStyles() {
    if (document.querySelector("link[data-ui-v4-workspace]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `/assets/ui-v4-workspace.css?v=${VERSION}`;
    link.dataset.uiV4Workspace = "true";
    document.head.appendChild(link);
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
    if (result.classList.contains("empty")) result.setAttribute("aria-label", config.emptyTitle);
  }

  function apply() {
    ensureStyles();
    if (!document.body) return;
    document.body.classList.add("ui-v4-workspace");
    document.documentElement.dataset.zhilinkWorkspace = "v4";
    Object.entries(MODULES).forEach(([id, config]) => decoratePage(id, config));
    window.ZHILINK_UI_V4_WORKSPACE_READY = true;
  }

  function queueApply() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      apply();
    });
  }

  function installObserver() {
    if (observer || !document.body) return;
    observer = new MutationObserver(mutations => {
      const relevant = mutations.some(mutation => {
        if (mutation.type === "attributes") return mutation.target?.classList?.contains("result-panel");
        return mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0;
      });
      if (relevant) queueApply();
    });
    observer.observe(document.querySelector(".main") || document.body, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["class"],
    });
  }

  function start() {
    apply();
    installObserver();
    window.addEventListener("zhilink:workspace-state-change", queueApply);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
