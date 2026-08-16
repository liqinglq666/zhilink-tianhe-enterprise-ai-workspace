/* UI V4 runtime: one core contract, hook/event bridge and presentation scheduler. */
(() => {
  if (!window.ZHILINK_UI_V4_HELPERS_READY) {
    function readJson(raw, fallback) {
      try { return raw ? JSON.parse(raw) : fallback; }
      catch (_) { return fallback; }
    }
    function setText(element, value) {
      if (element && element.textContent !== String(value)) element.textContent = String(value);
    }
    function escapeHtml(value) {
      return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
    }
    window.ZHILINK_UI_V4_HELPERS = Object.freeze({ readJson, setText, escapeHtml });
    window.ZHILINK_UI_V4_HELPERS_READY = true;
  }

  if (
    window.ZHILINK_UI_V4_RUNTIME_READY
    && window.ZHILINK_WORKSPACE_HOOKS_READY
    && window.ZHILINK_RESULT_EVENTS_READY
    && window.ZHILINK_WORKSPACE_CONTRACTS_READY
  ) return;

  const coreResultKeys = typeof resultKeys !== "undefined" ? Array.from(resultKeys) : [];
  const coreResultTitles = typeof resultTitles !== "undefined" ? { ...resultTitles } : {};
  const storage = Object.freeze({
    workspaceKey: "zhilian_workspace_key_v1",
    currentProject: "zhilian_current_project_v1",
    restoreSection: "zhilian_restore_section_v1",
    identity: "zhilian_identity",
    profile: "zhilian_profile",
    formInputs: "zhilian_form_inputs",
    results: "zhilian_results",
    meta: "zhilian_meta",
    structuredResults: "zhilian_structured_results_v1",
    exampleContexts: "zhilian_example_contexts_v1",
    legacyQuarantine: "zhilian_legacy_result_quarantine_v1",
  });
  const events = Object.freeze({
    accountReady: "zhilink:account-ready",
    workspaceStateChange: "zhilink:workspace-state-change",
    projectChanged: "zhilink:project-changed",
    dataProvenanceReady: "zhilink:data-provenance-ready",
    resultSchemaStamped: "zhilink:result-schema-stamped",
    modelModeChange: "zhilink:model-mode-change",
    resultUpdated: "zhilink:result-updated",
    progressUpdated: "zhilink:progress-updated",
    structuredUpdated: "zhilink:structured-updated",
    reviewUpdated: "zhilink:review-updated",
  });
  const modules = Object.freeze({
    home: Object.freeze({ label: "工作首页", group: "工作台", icon: "home", resultLabel: "" }),
    meeting: Object.freeze({ label: "会议纪要", group: "业务处理", icon: "meeting", resultLabel: "会议纪要 · AI 生成结果" }),
    contract: Object.freeze({ label: "合同审阅", group: "业务处理", icon: "contract", resultLabel: "合同风险 · AI 审阅结果" }),
    policy: Object.freeze({ label: "政策助手", group: "业务处理", icon: "policy", resultLabel: "政策方向 · AI 建议结果" }),
    match: Object.freeze({ label: "供需协作", group: "业务处理", icon: "match", resultLabel: "供需协作 · AI 方案结果" }),
    profile: Object.freeze({ label: "企业档案", group: "资料与执行", icon: "profile", resultLabel: "企业档案 · 生成结果" }),
    landing: Object.freeze({ label: "实施计划", group: "资料与执行", icon: "plan", resultLabel: "实施计划 · AI 生成结果" }),
    report: Object.freeze({ label: "报告归档", group: "归档", icon: "report", resultLabel: "运营报告 · 汇总与导出" }),
  });
  const moduleOrder = Object.freeze(["meeting", "contract", "policy", "match", "profile", "landing"]);
  const contracts = Object.freeze({
    resultKeys: Object.freeze(coreResultKeys),
    schemaResultKeys: Object.freeze([...coreResultKeys, "report"]),
    resultTitles: Object.freeze(coreResultTitles),
    modules,
    moduleOrder,
    storage,
    events,
    formalOrigins: Object.freeze(["user", "project", "imported"]),
  });
  window.ZHILINK_WORKSPACE_CONTRACTS = contracts;
  window.ZHILINK_WORKSPACE_CONTRACTS_READY = true;

  const icons = Object.freeze({
    menu: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    down: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg>',
    project: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3.5 6.5h6.7l2 2h8.3v10.5h-17z"/><path d="M3.5 9h17"/></svg>',
    knowledge: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h6a3 3 0 0 1 3 3v13a3 3 0 0 0-3-3H5z"/><path d="M19 4h-2a3 3 0 0 0-3 3v13a3 3 0 0 1 3-3h2z"/></svg>',
    home: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10.5V20h13v-9.5M9 20v-6h6v6"/></svg>',
    meeting: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3.5h9l3 3V21H6z"/><path d="M15 3.5V7h3M9 12h6M9 16h4"/></svg>',
    contract: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3.5h9l3 3V21H6z"/><path d="M15 3.5V7h3M9 11h5M9 15h3"/><circle cx="15.5" cy="15.5" r="4"/></svg>',
    policy: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9h16M6 9V7l6-3 6 3v2M7 9v8M11 9v8M15 9v8M19 17H5v3h14z"/></svg>',
    match: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8.5 12.5 11 15a2.4 2.4 0 0 0 3.4 0l4.1-4.1"/><path d="m9.5 8.5 2-2a2.8 2.8 0 0 1 4 0l4 4-3 3"/></svg>',
    profile: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20V8h8v12M12 20V4h8v16"/><path d="M7 11h2M7 14h2M15 7h2M15 10h2M15 13h2"/></svg>',
    plan: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M7 3v4M17 3v4M3.5 9h17"/></svg>',
    report: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3.5h9l3 3V21H6z"/><path d="M15 3.5V7h3M9 17v-3M12 17v-6M15 17v-4"/></svg>',
    account: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="3.5"/><path d="M5 20a7 7 0 0 1 14 0"/></svg>',
    arrow: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M14 7l5 5-5 5"/></svg>',
  });
  window.ZHILINK_UI_V4_ICONS = icons;
  window.ZHILINK_UI_V4_ICONS_READY = true;

  const hookHandlers = new Map();
  let generationTransport = null;

  function registerHook(kind, handler) {
    if (typeof handler !== "function") throw new TypeError(`Hook ${kind} must be a function.`);
    if (!hookHandlers.has(kind)) hookHandlers.set(kind, new Set());
    const bucket = hookHandlers.get(kind);
    bucket.add(handler);
    return () => bucket.delete(handler);
  }

  function runHookSync(kind, value) {
    let current = value;
    for (const handler of hookHandlers.get(kind) || []) {
      const next = handler(current);
      if (next && typeof next.then === "function") throw new TypeError(`Hook ${kind} must be synchronous.`);
      if (next !== undefined) current = next;
    }
    return current;
  }

  async function runHookAsync(kind, value) {
    let current = value;
    for (const handler of hookHandlers.get(kind) || []) {
      const next = await handler(current);
      if (next !== undefined) current = next;
    }
    return current;
  }

  function setGenerationTransport(handler) {
    if (typeof handler !== "function") throw new TypeError("Generation transport must be a function.");
    if (generationTransport && generationTransport !== handler) throw new Error("Generation transport is already registered.");
    generationTransport = handler;
  }

  const originalApiStream = typeof apiStream === "function" ? apiStream : null;
  const originalCollectResultsForReport = typeof collectResultsForReport === "function" ? collectResultsForReport : null;
  const originalCollectSingleModuleResult = typeof collectSingleModuleResult === "function" ? collectSingleModuleResult : null;
  const originalFetch = window.fetch.bind(window);

  function requestUrl(input) {
    try {
      const raw = typeof input === "string" ? input : input?.url || "";
      return new URL(raw, location.origin);
    } catch (_) {
      return null;
    }
  }

  function requestMethod(input, init) {
    return String(init?.method || (typeof input !== "string" ? input?.method : "") || "GET").toUpperCase();
  }

  function isProjectWrite(input, init) {
    const url = requestUrl(input);
    const method = requestMethod(input, init);
    return Boolean(url && url.origin === location.origin && url.pathname.startsWith("/api/projects") && ["POST", "PUT", "PATCH", "DELETE"].includes(method));
  }

  if (originalApiStream) {
    apiStream = async function hookedApiStream(url, payload, key) {
      const request = await runHookAsync("generation:request", { url, payload, key });
      const transport = generationTransport || (context => originalApiStream(context.url, context.payload, context.key));
      return transport(request);
    };
  }

  if (originalCollectResultsForReport) {
    collectResultsForReport = function hookedCollectResultsForReport(includeAiSummary = false) {
      const results = originalCollectResultsForReport.apply(this, arguments);
      const context = runHookSync("results:collect", {
        scope: "report",
        includeAiSummary: Boolean(includeAiSummary),
        results: { ...(results || {}) },
      });
      return context?.results || results;
    };
  }

  if (originalCollectSingleModuleResult) {
    collectSingleModuleResult = function hookedCollectSingleModuleResult(key) {
      const result = originalCollectSingleModuleResult.apply(this, arguments);
      const context = runHookSync("results:collect", { scope: "single", key, result });
      return context?.result || result;
    };
  }

  function emitWindowEvent(name, detail) {
    window.dispatchEvent(new CustomEvent(name, { detail }));
  }

  window.fetch = async function hookedWorkspaceFetch(input, init = {}) {
    const request = await runHookAsync("fetch:request", { input, init });
    const finalInput = request?.input ?? input;
    const finalInit = request?.init ?? init;
    const response = await originalFetch(finalInput, finalInit);
    if (response.ok && isProjectWrite(finalInput, finalInit)) {
      const url = requestUrl(finalInput);
      emitWindowEvent(events.projectChanged, {
        method: requestMethod(finalInput, finalInit),
        path: url?.pathname || "",
      });
    }
    return response;
  };

  window.ZHILINK_WORKSPACE_HOOKS = {
    register: registerHook,
    runSync: runHookSync,
    runAsync: runHookAsync,
    setGenerationTransport,
    hasGenerationTransport: () => Boolean(generationTransport),
  };
  window.ZHILINK_WORKSPACE_HOOKS_READY = true;

  const RESULT_EVENT = events.resultUpdated;
  const PROGRESS_EVENT = events.progressUpdated;
  let commitDepth = 0;

  const originalShowResult = window.showResult;
  const originalSetResult = window.setResult;
  const originalUpdateProgress = window.updateProgress;

  if (typeof originalShowResult === "function" && typeof originalSetResult === "function" && typeof originalUpdateProgress === "function") {
    window.showResult = function eventAwareShowResult(key, result) {
      const value = originalShowResult.apply(this, arguments);
      emitWindowEvent(RESULT_EVENT, {
        key,
        result: result || {},
        content: String(result?.content || (typeof state !== "undefined" ? state.results?.[key] || "" : "")),
        meta: typeof state !== "undefined" ? state.meta?.[key] || {} : {},
        source: commitDepth > 0 ? "commit" : "render",
      });
      return value;
    };

    window.setResult = function eventAwareSetResult(key, result) {
      commitDepth += 1;
      try { return originalSetResult.apply(this, arguments); }
      finally { commitDepth -= 1; }
    };

    window.updateProgress = function eventAwareUpdateProgress() {
      const value = originalUpdateProgress.apply(this, arguments);
      const results = typeof state !== "undefined" ? state.results || {} : {};
      emitWindowEvent(PROGRESS_EVENT, {
        done: contracts.resultKeys.filter(key => Boolean(results[key])).length,
        total: contracts.resultKeys.length,
      });
      return value;
    };
  } else {
    console.error("结果事件桥接器初始化失败：核心结果函数不可用。");
  }

  window.ZHILINK_RESULT_EVENTS = {
    resultEvent: RESULT_EVENT,
    progressEvent: PROGRESS_EVENT,
  };
  window.ZHILINK_RESULT_EVENTS_READY = true;

  const subscribers = new Set();
  const EVENT_NAMES = [
    events.accountReady,
    events.workspaceStateChange,
    events.projectChanged,
    events.dataProvenanceReady,
    events.resultSchemaStamped,
    events.modelModeChange,
  ];
  let observer = null;
  let queued = false;
  let started = false;
  let lastReason = "startup";

  function runSubscribers() {
    queued = false;
    const reason = lastReason;
    lastReason = "runtime";
    subscribers.forEach(callback => {
      try { callback(reason); }
      catch (error) { console.error("UI V4 runtime subscriber failed", error); }
    });
  }

  function schedule(reason = "runtime") {
    lastReason = reason;
    if (queued) return;
    queued = true;
    requestAnimationFrame(runSubscribers);
  }

  function subscribe(callback, { immediate = true } = {}) {
    if (typeof callback !== "function") return () => {};
    subscribers.add(callback);
    if (immediate) {
      try { callback("subscribe"); }
      catch (error) { console.error("UI V4 runtime subscriber failed", error); }
    }
    return () => subscribers.delete(callback);
  }

  function emit(name, detail = {}) {
    emitWindowEvent(name, detail);
    schedule(name);
  }

  function installObserver() {
    if (observer || !document.body) return;
    observer = new MutationObserver(mutations => {
      const relevant = mutations.some(mutation => {
        if (mutation.type === "characterData") return true;
        if (mutation.type === "childList") return mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0;
        return mutation.type === "attributes" && ["class", "hidden", "aria-hidden", "aria-expanded", "disabled"].includes(mutation.attributeName);
      });
      if (relevant) schedule("dom");
    });
    observer.observe(document.body, {
      subtree: true,
      childList: true,
      characterData: true,
      attributes: true,
      attributeFilter: ["class", "hidden", "aria-hidden", "aria-expanded", "disabled"],
    });
  }

  function start() {
    if (started) return;
    started = true;
    installObserver();
    EVENT_NAMES.forEach(name => window.addEventListener(name, () => schedule(name)));
    window.addEventListener("storage", () => schedule("storage"));
    window.addEventListener("resize", () => schedule("resize"), { passive: true });
    window.addEventListener("orientationchange", () => schedule("orientationchange"), { passive: true });
    schedule("startup");
    window.ZHILINK_UI_V4_RUNTIME_READY = true;
  }

  window.ZHILINK_UI_V4_RUNTIME = {
    subscribe,
    schedule,
    emit,
    refresh: () => schedule("manual"),
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
