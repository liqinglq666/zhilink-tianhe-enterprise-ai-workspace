/* Keep the derived operations report consistent with its source materials. */
(() => {
  const REPORT_REFRESH_MODE = "需更新";
  const originalSetResult = setResult;
  const originalShowResult = showResult;
  const originalCollectResultsForReport = collectResultsForReport;
  const originalUpdateProgress = updateProgress;

  function reportNeedsRefresh() {
    return !state.results.report && state.meta?.report?.mode === REPORT_REFRESH_MODE;
  }

  function invalidateReportIfSourceChanged(key, nextContent) {
    if (key === "report" || !state.results.report) return false;
    const previousContent = String(state.results[key] || "");
    const incomingContent = String(nextContent || "");
    if (previousContent === incomingContent) return false;

    const previousMeta = state.meta?.report || {};
    delete state.results.report;
    state.meta.report = {
      ...previousMeta,
      mode: REPORT_REFRESH_MODE,
      error: "",
    };
    return true;
  }

  showResult = function showFreshResult(key, result, source = "render") {
    if (key === "report" && (!result || !result.content) && reportNeedsRefresh()) {
      const panel = $("reportResult");
      if (!panel) return;
      panel.className = "result-panel empty report-needs-refresh";
      panel.innerHTML = [
        "<strong>运营报告需更新</strong>",
        "<span>源材料已发生变化，之前的运营报告已失效，请重新整合。</span>",
        "<small>重新整合前，导出只包含最新源材料，不会混入旧的 AI 整合报告。</small>",
      ].join("");
      emitResultUpdated(key, result || {}, source);
      return;
    }
    return originalShowResult(key, result, source);
  };

  updateProgress = function updateFreshProgress() {
    originalUpdateProgress();
    const stale = reportNeedsRefresh();
    const reportStatus = document.querySelector('.tool-status-item[data-goto="report"] strong');
    if (reportStatus && stale) reportStatus.textContent = "需更新";

    const reportNav = document.querySelector('.nav button[data-section="report"]');
    if (reportNav) {
      reportNav.classList.toggle("done", Boolean(state.results.report) && !stale);
      reportNav.classList.toggle("needs-refresh", stale);
      reportNav.title = stale ? "源材料已更新，请重新整合运营报告" : "";
    }

    const runButton = $("runReport");
    if (runButton && !runButton.classList.contains("loading")) {
      runButton.textContent = stale ? "重新整合运营报告" : "AI 整合运营报告";
    }

    if (stale) showResult("report", {}, "stale");
  };

  collectResultsForReport = function collectFreshResultsForReport(includeAiSummary = false) {
    if (reportNeedsRefresh()) {
      return originalCollectResultsForReport(false);
    }
    return originalCollectResultsForReport(includeAiSummary);
  };

  setResult = function setFreshResult(key, result) {
    const invalidated = invalidateReportIfSourceChanged(key, result?.content || "");
    originalSetResult(key, result);
    if (invalidated) showResult("report", {}, "stale");
  };

  updateProgress();
})();
