/* Default simple product mode: keep enterprise capabilities without overwhelming the main workspace. */
(() => {
  const MODE_STORAGE = "zhilian_ui_mode_v1";
  const CURRENT_PROJECT_STORAGE = "zhilian_current_project_v1";
  const SIMPLE = "simple";
  const ADVANCED = "advanced";
  let scheduled = false;

  function read(raw, fallback = null) {
    try { return raw ? JSON.parse(raw) : fallback; } catch (_) { return fallback; }
  }

  function mode() {
    return localStorage.getItem(MODE_STORAGE) === ADVANCED ? ADVANCED : SIMPLE;
  }

  function setMode(next) {
    localStorage.setItem(MODE_STORAGE, next === ADVANCED ? ADVANCED : SIMPLE);
    document.querySelectorAll(".ui-show-advanced").forEach(element => element.classList.remove("ui-show-advanced"));
    apply();
    window.dispatchEvent(new CustomEvent("zhilink:ui-mode-changed", { detail: { mode: mode() } }));
  }

  function activeOrganization() {
    return window.ZHILINK_ACCOUNT?.getActiveOrganization?.() || null;
  }

  function currentProject() {
    return read(localStorage.getItem(CURRENT_PROJECT_STORAGE), null);
  }

  function injectStylesheet() {
    if (document.querySelector("link[data-product-simplification]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "/assets/product-simplification.css";
    link.dataset.productSimplification = "true";
    document.head.appendChild(link);
  }

  function setText(element, value) {
    if (element && element.textContent !== value) element.textContent = value;
  }

  function compactTopActions(simple) {
    const top = document.querySelector(".top-actions");
    if (!top) return;
    const projectButton = document.getElementById("openProjectManager");
    const knowledgeButton = document.getElementById("openKnowledgeBase");
    const accountButton = document.getElementById("openAccountManager");
    const serviceButton = document.getElementById("openServiceWorkflow");
    const reportButton = top.querySelector('[data-goto="report"]');

    let anchor = reportButton || null;
    [accountButton, knowledgeButton, projectButton].forEach(button => {
      if (!button || button.parentElement !== top) return;
      if (button.nextElementSibling !== anchor) top.insertBefore(button, anchor);
      anchor = button;
    });

    if (serviceButton) {
      serviceButton.hidden = simple;
      serviceButton.setAttribute("aria-hidden", simple ? "true" : "false");
    }

    if (!simple) return;
    if (projectButton) {
      const dirty = projectButton.classList.contains("project-dirty");
      setText(projectButton, dirty ? "项目 · 未保存" : "项目");
    }
    if (accountButton) {
      setText(accountButton, document.body.dataset.authenticated === "true" ? "账户" : "登录");
    }
    setText(knowledgeButton, "知识库");
  }

  function closeProjectManager() {
    document.querySelector("#projectManagerModal [data-close-project-manager]")?.click();
  }

  function openServiceWorkflow() {
    const project = currentProject();
    if (!activeOrganization()) {
      if (typeof toast === "function") toast("请先登录并选择组织空间。");
      return;
    }
    if (!project?.id) {
      if (typeof toast === "function") toast("请先创建或打开一个已保存项目。");
      return;
    }
    closeProjectManager();
    const direct = window.ZHILINK_SERVICE_WORKFLOW?.open;
    if (typeof direct === "function") direct();
    else document.getElementById("openServiceWorkflow")?.click();
  }

  function ensureProjectTools(simple) {
    const row = document.querySelector("#projectManagerModal .project-action-row");
    if (!row) return;

    let service = document.getElementById("openServiceWorkflowFromProject");
    if (!service) {
      service = document.createElement("button");
      service.id = "openServiceWorkflowFromProject";
      service.className = "ghost ui-project-secondary-tool";
      service.type = "button";
      service.textContent = "服务跟进";
      service.addEventListener("click", openServiceWorkflow);
      row.appendChild(service);
    }
    const project = currentProject();
    const organization = activeOrganization();
    service.hidden = !simple || !organization;
    service.disabled = !project?.id;
    service.title = project?.id ? "打开当前项目的服务跟进流程" : "请先创建或打开项目";

    let toggle = document.getElementById("toggleAdvancedUiMode");
    if (!toggle) {
      toggle = document.createElement("button");
      toggle.id = "toggleAdvancedUiMode";
      toggle.className = "ghost ui-mode-toggle";
      toggle.type = "button";
      toggle.addEventListener("click", () => setMode(mode() === SIMPLE ? ADVANCED : SIMPLE));
      row.appendChild(toggle);
    }
    setText(toggle, simple ? "显示高级功能" : "返回精简模式");
    toggle.title = simple ? "显示完整 JSON、哈希、审计记录和顶部服务流程入口" : "收起技术信息和次要管理入口";
  }

  function ensureAdvancedToggle(modalSelector, headerSelector, id, label) {
    const modal = document.querySelector(modalSelector);
    const header = modal?.querySelector(headerSelector);
    if (!modal || !header || document.getElementById(id)) return;
    const button = document.createElement("button");
    button.id = id;
    button.className = "ghost small ui-local-advanced-toggle";
    button.type = "button";
    button.textContent = label;
    button.addEventListener("click", () => {
      modal.classList.toggle("ui-show-advanced");
      button.textContent = modal.classList.contains("ui-show-advanced") ? "收起高级信息" : label;
      markTechnicalDetails(modal);
    });
    const closeButton = header.querySelector(".icon-btn");
    header.insertBefore(button, closeButton || null);
  }

  function simplifyStructured(simple) {
    const modal = document.getElementById("structuredResultModal");
    document.querySelectorAll("[data-open-structured]").forEach(button => {
      setText(button, simple ? "结构化结果" : "查看 JSON");
    });
    if (!modal) return;
    const track = modal.querySelector(".track");
    setText(track, simple ? "结果核对" : "结构化 JSON");
    const intro = modal.querySelector(".structured-dialog-header p");
    setText(
      intro,
      simple
        ? "查看输入事实、AI 推断、风险和待确认项。"
        : "该 JSON 由服务端根据当前 Markdown 确定性生成，不会再次调用模型。",
    );
    ensureAdvancedToggle("#structuredResultModal", ".structured-dialog-header", "toggleStructuredAdvanced", "显示 JSON 与校验信息");
  }

  function simplifyKnowledge() {
    ensureAdvancedToggle("#knowledgeBaseModal", ".knowledge-dialog-header", "toggleKnowledgeAdvanced", "显示版本与审核记录");
  }

  function simplifyReview() {
    ensureAdvancedToggle("#reviewWorkflowModal", ".review-dialog-header", "toggleReviewAdvanced", "显示审核记录");
  }

  function groupWorkflowNodes() {
    const container = document.querySelector("#swDetail .sw-nodes");
    if (!container) return;
    const nodes = Array.from(container.querySelectorAll(":scope > .sw-node"));
    if (!nodes.length) return;
    const phases = [
      [0, "collect", "第 1 步 · 收集需求"],
      [2, "process", "第 2 步 · 处理与跟进"],
      [4, "close", "第 3 步 · 完成与归档"],
    ];
    phases.forEach(([index, key, label]) => {
      const node = nodes[index];
      if (!node) return;
      let heading = container.querySelector(`:scope > .ui-workflow-phase[data-ui-phase="${key}"]`);
      if (!heading) {
        heading = document.createElement("div");
        heading.className = "ui-workflow-phase";
        heading.dataset.uiPhase = key;
        heading.textContent = label;
      }
      if (heading.nextElementSibling !== node) container.insertBefore(heading, node);
    });
  }

  function markWorkflowAdvanced() {
    const detail = document.getElementById("swDetail");
    if (!detail) return;
    detail.querySelectorAll(":scope > .sw-card").forEach(card => {
      const heading = card.querySelector("h4");
      card.classList.toggle("ui-workflow-audit-card", heading?.textContent.trim() === "操作记录");
    });
    groupWorkflowNodes();
  }

  function markTechnicalDetails(root = document) {
    const technical = /(SHA-?256|source_sha256|payload_sha256|context_sha256|内容哈希|载荷哈希)/i;
    root.querySelectorAll("small, span, p, code").forEach(element => {
      if (technical.test(element.textContent || "")) element.classList.add("ui-technical-detail");
    });
  }

  function apply() {
    injectStylesheet();
    const simple = mode() === SIMPLE;
    document.body.classList.toggle("ui-simple-mode", simple);
    document.body.classList.toggle("ui-advanced-mode", !simple);
    document.body.dataset.uiMode = simple ? SIMPLE : ADVANCED;
    compactTopActions(simple);
    ensureProjectTools(simple);
    simplifyStructured(simple);
    simplifyKnowledge();
    simplifyReview();
    markWorkflowAdvanced();
    markTechnicalDetails();
  }

  function scheduleApply() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      apply();
    });
  }

  injectStylesheet();
  apply();
  new MutationObserver(scheduleApply).observe(document.documentElement, { childList: true, subtree: true });
  document.addEventListener("zhilink:account-ready", scheduleApply);
  window.addEventListener("storage", event => {
    if ([MODE_STORAGE, CURRENT_PROJECT_STORAGE].includes(event.key)) scheduleApply();
  });

  window.ZHILINK_UI_MODE = {
    get: mode,
    set: setMode,
    toggle: () => setMode(mode() === SIMPLE ? ADVANCED : SIMPLE),
  };
  window.ZHILINK_SIMPLE_UI_READY = true;
})();
