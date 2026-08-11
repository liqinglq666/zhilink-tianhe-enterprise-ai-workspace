/* UI V4 runtime: one core contract, hook/event bridge and presentation scheduler. */
(() => {
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
  const contracts = Object.freeze({
    resultKeys: Object.freeze(coreResultKeys),
    schemaResultKeys: Object.freeze([...coreResultKeys, "report"]),
    resultTitles: Object.freeze(coreResultTitles),
    storage,
    events,
    formalOrigins: Object.freeze(["user", "project", "imported"]),
  });
  window.ZHILINK_WORKSPACE_CONTRACTS = contracts;
  window.ZHILINK_WORKSPACE_CONTRACTS_READY = true;

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
