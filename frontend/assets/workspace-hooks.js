/* Single compatibility bridge for generation, result collection, and request hooks. */
(() => {
  if (window.ZHILINK_WORKSPACE_HOOKS) return;

  const handlers = new Map();
  let generationTransport = null;

  function register(kind, handler) {
    if (typeof handler !== "function") throw new TypeError(`Hook ${kind} must be a function.`);
    if (!handlers.has(kind)) handlers.set(kind, new Set());
    const bucket = handlers.get(kind);
    bucket.add(handler);
    return () => bucket.delete(handler);
  }

  function runSync(kind, value) {
    let current = value;
    for (const handler of handlers.get(kind) || []) {
      const next = handler(current);
      if (next && typeof next.then === "function") {
        throw new TypeError(`Hook ${kind} must be synchronous.`);
      }
      if (next !== undefined) current = next;
    }
    return current;
  }

  async function runAsync(kind, value) {
    let current = value;
    for (const handler of handlers.get(kind) || []) {
      const next = await handler(current);
      if (next !== undefined) current = next;
    }
    return current;
  }

  function setGenerationTransport(handler) {
    if (typeof handler !== "function") throw new TypeError("Generation transport must be a function.");
    if (generationTransport && generationTransport !== handler) {
      throw new Error("Generation transport is already registered.");
    }
    generationTransport = handler;
  }

  const originalApiStream = typeof apiStream === "function" ? apiStream : null;
  if (originalApiStream) {
    apiStream = async function hookedApiStream(url, payload, key) {
      const request = await runAsync("generation:request", { url, payload, key });
      const transport = generationTransport || (context => originalApiStream(context.url, context.payload, context.key));
      return transport(request);
    };
  }

  const originalCollectResultsForReport = typeof collectResultsForReport === "function" ? collectResultsForReport : null;
  if (originalCollectResultsForReport) {
    collectResultsForReport = function hookedCollectResultsForReport(includeAiSummary = false) {
      const results = originalCollectResultsForReport.apply(this, arguments);
      const context = runSync("results:collect", {
        scope: "report",
        includeAiSummary: Boolean(includeAiSummary),
        results: { ...(results || {}) },
      });
      return context?.results || results;
    };
  }

  const originalCollectSingleModuleResult = typeof collectSingleModuleResult === "function" ? collectSingleModuleResult : null;
  if (originalCollectSingleModuleResult) {
    collectSingleModuleResult = function hookedCollectSingleModuleResult(key) {
      const result = originalCollectSingleModuleResult.apply(this, arguments);
      const context = runSync("results:collect", { scope: "single", key, result });
      return context?.result || result;
    };
  }

  const originalFetch = window.fetch.bind(window);
  window.fetch = async function hookedWorkspaceFetch(input, init = {}) {
    const request = await runAsync("fetch:request", { input, init });
    return originalFetch(request?.input ?? input, request?.init ?? init);
  };

  window.ZHILINK_WORKSPACE_HOOKS = {
    register,
    runSync,
    runAsync,
    setGenerationTransport,
    hasGenerationTransport: () => Boolean(generationTransport),
  };
  window.ZHILINK_WORKSPACE_HOOKS_READY = true;
})();
