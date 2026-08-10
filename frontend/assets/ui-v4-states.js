/* UI V4 states: consistent empty, loading, error and feedback presentation without owning business state. */
(() => {
  const VERSION = "20260810.1";
  const STATE_SELECTOR = [
    ".result-panel",
    ".project-empty",
    ".knowledge-empty",
    ".knowledge-error",
    ".knowledge-search-empty",
    ".account-empty",
    ".recent-list.empty",
    "#connectionResult",
    "#toast",
  ].join(",");

  let observer = null;
  let queued = false;

  function ensureStyles() {
    if (document.querySelector("link[data-ui-v4-states]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `/assets/ui-v4-states.css?v=${VERSION}`;
    link.dataset.uiV4States = "true";
    document.head.appendChild(link);
  }

  function normalizedText(element) {
    return String(element?.textContent || "").replace(/\s+/g, " ").trim();
  }

  function classifyText(text) {
    if (!text) return "idle";
    if (/(失败|错误|异常|超时|不可用|不存在|无权|冲突|中断|未完成)/.test(text)) return "error";
    if (/(正在|读取中|加载中|生成中|连接中|检索中|导出中|保存中|测试中|请稍候)/.test(text)) return "loading";
    if (/(未保存|待确认|需确认|注意|警告|风险)/.test(text)) return "warning";
    if (/(成功|已保存|已创建|已完成|已复制|已归档|已恢复|已发布|已批准|已提交|已开始下载)/.test(text)) return "success";
    return "info";
  }

  function setAriaState(element, state) {
    if (!(element instanceof HTMLElement)) return;
    if (state === "error") {
      element.setAttribute("role", "alert");
      element.setAttribute("aria-live", "assertive");
      return;
    }
    if (["loading", "success", "warning"].includes(state)) {
      element.setAttribute("role", "status");
      element.setAttribute("aria-live", "polite");
    }
  }

  function actionOrientedEmptyCopy(element) {
    if (!(element instanceof HTMLElement)) return;
    const text = normalizedText(element);
    if (element.matches(".recent-list.empty") && /暂无生成材料|暂无.*材料/.test(text)) {
      element.textContent = "还没有最近材料。完成一次业务任务后，生成结果会出现在这里。";
      return;
    }
    if (element.closest("#projectList") && /暂无|还没有|没有.*项目/.test(text)) {
      element.textContent = "还没有项目。创建项目后，可保存当前工作内容和版本历史。";
      return;
    }
    if (element.closest("#projectHistoryList") && /暂无|还没有|没有.*版本/.test(text)) {
      element.textContent = "当前项目还没有版本记录。保存项目后，版本历史会显示在这里。";
      return;
    }
    if (element.closest("#knowledgeArticleList") && /还没有可见的知识条目|暂无/.test(text)) {
      element.textContent = "当前组织还没有知识条目。新建草稿并审核通过后，可用于知识检索。";
      return;
    }
    if (element.closest("#knowledgeEditor") && /选择一个知识条目/.test(text)) {
      element.textContent = "选择左侧知识条目查看详情，或新建一个草稿。";
    }
  }

  function decorateResultPanel(panel) {
    if (!(panel instanceof HTMLElement)) return;
    panel.classList.add("ui-v4-state-surface");
    if (panel.classList.contains("streaming")) {
      panel.dataset.uiV4State = "loading";
      panel.setAttribute("aria-busy", "true");
      panel.setAttribute("aria-live", "polite");
      return;
    }
    panel.removeAttribute("aria-busy");
    if (panel.classList.contains("empty")) {
      panel.dataset.uiV4State = "empty";
      return;
    }
    const text = normalizedText(panel);
    panel.dataset.uiV4State = /(生成失败|调用异常|失败|错误|超时)/.test(text) ? "error" : "ready";
    setAriaState(panel, panel.dataset.uiV4State);
  }

  function decorateGeneric(element) {
    if (!(element instanceof HTMLElement)) return;
    actionOrientedEmptyCopy(element);
    const text = normalizedText(element);
    let state = classifyText(text);

    if (element.matches(".project-empty, .knowledge-empty, .knowledge-search-empty, .account-empty, .recent-list.empty")) {
      state = state === "loading" || state === "error" ? state : "empty";
    }
    if (element.matches(".knowledge-error, .project-empty.error, .account-empty.error")) state = "error";

    element.classList.add("ui-v4-state-surface");
    element.dataset.uiV4State = state;
    if (state === "loading") element.setAttribute("aria-busy", "true");
    else element.removeAttribute("aria-busy");
    setAriaState(element, state);
  }

  function decorateConnectionResult(element) {
    if (!(element instanceof HTMLElement)) return;
    const text = normalizedText(element);
    if (!text) {
      element.removeAttribute("data-ui-v4-state");
      return;
    }
    const state = classifyText(text);
    element.dataset.uiV4State = state;
    element.classList.add("ui-v4-inline-feedback");
    setAriaState(element, state);
  }

  function decorateToast(element) {
    if (!(element instanceof HTMLElement)) return;
    const text = normalizedText(element);
    const state = classifyText(text);
    element.dataset.uiV4State = state;
    element.setAttribute("role", state === "error" ? "alert" : "status");
    element.setAttribute("aria-live", state === "error" ? "assertive" : "polite");
    element.setAttribute("aria-atomic", "true");
  }

  function decorateLoadingButtons(root = document) {
    root.querySelectorAll?.("button.loading, button[aria-busy='true']").forEach(button => {
      button.classList.add("ui-v4-loading-control");
      button.setAttribute("aria-busy", "true");
    });
    root.querySelectorAll?.("button.ui-v4-loading-control:not(.loading):not([aria-busy='true'])").forEach(button => {
      button.classList.remove("ui-v4-loading-control");
      button.removeAttribute("aria-busy");
    });
  }

  function decorateDisabledControls(root = document) {
    root.querySelectorAll?.("button:disabled, input:disabled, select:disabled, textarea:disabled").forEach(control => {
      control.dataset.uiV4Disabled = "true";
    });
    root.querySelectorAll?.("[data-ui-v4-disabled='true']:not(:disabled)").forEach(control => {
      delete control.dataset.uiV4Disabled;
    });
  }

  function sync(root = document) {
    root.querySelectorAll?.(STATE_SELECTOR).forEach(element => {
      if (element.matches(".result-panel")) decorateResultPanel(element);
      else if (element.id === "connectionResult") decorateConnectionResult(element);
      else if (element.id === "toast") decorateToast(element);
      else decorateGeneric(element);
    });
    decorateLoadingButtons(root);
    decorateDisabledControls(root);
  }

  function queueSync() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      sync(document);
    });
  }

  function installObserver() {
    if (observer || !document.body) return;
    observer = new MutationObserver(mutations => {
      const relevant = mutations.some(mutation => {
        if (mutation.type === "characterData") return true;
        if (mutation.type === "childList") return mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0;
        return mutation.type === "attributes" && ["class", "disabled", "aria-busy"].includes(mutation.attributeName);
      });
      if (relevant) queueSync();
    });
    observer.observe(document.body, {
      subtree: true,
      childList: true,
      characterData: true,
      attributes: true,
      attributeFilter: ["class", "disabled", "aria-busy"],
    });
  }

  function start() {
    ensureStyles();
    document.body.classList.add("ui-v4-states");
    sync(document);
    installObserver();
    window.ZHILINK_UI_V4_STATES_READY = true;
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
