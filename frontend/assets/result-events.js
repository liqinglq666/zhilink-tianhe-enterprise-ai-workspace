/* One bridge between legacy business functions and event-driven presentation layers. */
(() => {
  if (window.ZHILINK_RESULT_EVENTS_READY) return;

  const RESULT_EVENT = "zhilink:result-updated";
  const PROGRESS_EVENT = "zhilink:progress-updated";
  let commitDepth = 0;

  function emit(name, detail) {
    window.dispatchEvent(new CustomEvent(name, { detail }));
  }

  const originalShowResult = window.showResult;
  const originalSetResult = window.setResult;
  const originalUpdateProgress = window.updateProgress;

  if (typeof originalShowResult !== "function" || typeof originalSetResult !== "function" || typeof originalUpdateProgress !== "function") {
    console.error("结果事件桥接器初始化失败：核心结果函数不可用。");
    return;
  }

  window.showResult = function eventAwareShowResult(key, result) {
    const value = originalShowResult.apply(this, arguments);
    emit(RESULT_EVENT, {
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
    try {
      return originalSetResult.apply(this, arguments);
    } finally {
      commitDepth -= 1;
    }
  };

  window.updateProgress = function eventAwareUpdateProgress() {
    const value = originalUpdateProgress.apply(this, arguments);
    const results = typeof state !== "undefined" ? state.results || {} : {};
    const keys = typeof resultKeys !== "undefined" ? resultKeys : [];
    emit(PROGRESS_EVENT, {
      done: keys.filter(key => Boolean(results[key])).length,
      total: keys.length,
    });
    return value;
  };

  window.ZHILINK_RESULT_EVENTS = {
    resultEvent: RESULT_EVENT,
    progressEvent: PROGRESS_EVENT,
  };
  window.ZHILINK_RESULT_EVENTS_READY = true;
})();
