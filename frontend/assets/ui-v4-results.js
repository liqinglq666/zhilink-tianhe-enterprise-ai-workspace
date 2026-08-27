/* UI V4 results: owns result presentation chrome, copy/export actions and document utilities. */
(() => {
  const PANEL_SELECTOR = ".result-panel";
  const REQUEST_TIMEOUT_MS = 180000;
  const INTERNAL_META_RE = /(AI\s*模型|流式模式|模型模式|本地报告模式|含证据索引|本地规则预检|连接超时|生成超时|请求已发送|服务端协调)/i;
  const EXPORT_TECHNICAL_DETAIL_RE = /(?:traceback|exception|internal server error|bad gateway|gateway timeout|nginx|cloudflare|uvicorn|fastapi|sql(?:alchemy)?|api[_ -]?key|base[_ -]?url|stack trace|<html|<!doctype)/i;
  const KIND_RULES = [
    ["pending", /(待确认|待补充|需确认|未确认|信息缺口|未知事项|待核实)/],
    ["risk", /(风险|问题|注意事项|合规|警示|隐患|异常)/],
    ["decision", /(关键决策|会议决策|决定事项|已确认事项|核心结论|结论)/],
    ["action", /(待办|行动|下一步|执行|任务|实施|跟进|建议动作|工作安排)/],
    ["evidence", /(生成依据|来源|证据|参考材料|政策依据|原文依据)/],
    ["summary", /(摘要|概览|总结|总体判断|一句话|核心信息)/],
  ];
  const KIND_LABELS = { summary: "摘要", decision: "决策", action: "执行", risk: "风险", pending: "待确认", evidence: "依据" };
  const RECORD_KINDS = new Set(["action", "decision", "risk", "pending"]);
  const STATUS_HEADER_RE = /(确认状态|状态|风险等级|优先级|处理状态)/;
  let actionsBound = false;
  let resultSyncScheduled = false;

  function cleanText(value) { return String(value || "").replace(/\s+/g, " ").trim(); }
  function moduleFromPanel(panel) {
    const id = String(panel?.id || "");
    return id.endsWith("Result") ? id.slice(0, -6) : "result";
  }
  function sectionKind(title) {
    const value = cleanText(title);
    for (const [kind, pattern] of KIND_RULES) if (pattern.test(value)) return kind;
    return "default";
  }

  async function copyText(text) {
    const value = String(text || "");
    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(value);
        return;
      } catch (_) {}
    }
    const textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    try {
      textarea.focus();
      textarea.select();
      const copied = document.execCommand("copy");
      if (!copied) throw new Error("复制失败，请手动选择文本复制。");
    } finally {
      textarea.remove();
    }
  }

  function downloadTextFile(filename, content, contentType = "text/plain;charset=utf-8") {
    const blob = new Blob([String(content || "")], { type: contentType });
    const anchor = document.createElement("a");
    const objectUrl = URL.createObjectURL(blob);
    anchor.href = objectUrl;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  }

  function exportFailureMessage(status, detail) {
    const code = Number(status || 0);
    if (code === 413) return "导出内容过大，请精简后重试。";
    if (code === 401 || code === 403) return "导出请求未通过权限校验，请刷新页面后重试。";
    if (code === 404) return "导出服务暂时不可用，请稍后重试。";
    if (code === 429) return "导出请求较多，请稍后重试。";
    if (code >= 500) return "导出服务暂时不可用，请稍后重试。";
    const message = typeof detail === "string" ? cleanText(detail) : "";
    if ((code === 400 || code === 422) && message && message.length <= 120 && !EXPORT_TECHNICAL_DETAIL_RE.test(message)) return message;
    return "导出失败，请检查结果后重试。";
  }

  async function requestDownload(url, payload, filename, contentType, emptyMessage, timeoutMessage) {
    const hasContent = payload && payload.results && Object.values(payload.results).some(Boolean);
    if (!hasContent) throw new Error(emptyMessage || "还没有可导出的结果。");
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });
      if (!response.ok) {
        let detail = "";
        if (response.status === 400 || response.status === 422) {
          try {
            const data = await response.json();
            if (typeof data?.detail === "string") detail = data.detail;
          } catch (_) {}
        }
        const failure = new Error(exportFailureMessage(response.status, detail));
        failure.name = "ExportRequestError";
        throw failure;
      }
      const blob = await response.blob();
      const anchor = document.createElement("a");
      const objectUrl = URL.createObjectURL(new Blob([blob], { type: contentType }));
      anchor.href = objectUrl;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    } catch (error) {
      if (error.name === "AbortError") throw new Error(timeoutMessage || "导出超时，请稍后重试。");
      if (error.name === "ExportRequestError") throw error;
      throw new Error("网络连接异常，导出未完成，请稍后重试。");
    } finally {
      clearTimeout(timer);
    }
  }

  async function downloadReportFile(url, filename, contentType) {
    if (typeof collectResultsForReport !== "function") throw new Error("结果汇总模块未就绪。");
    const results = collectResultsForReport(true);
    await requestDownload(
      url,
      { results, use_ai_summary: false },
      filename,
      contentType,
      "还没有可导出的结果。",
      "报告导出超时，请精简结果内容后重试。",
    );
  }

  async function downloadModuleFile(key, format) {
    if (typeof collectSingleModuleResult !== "function") throw new Error("结果汇总模块未就绪。");
    const single = collectSingleModuleResult(key);
    if (!single.content) throw new Error("当前模块还没有生成结果，请先点击生成。");
    const safeTitle = single.title.replace(/[\/:*?"<>|]/g, "_");
    const formats = {
      md: ["/api/report/markdown", `${safeTitle}.md`, "text/markdown;charset=utf-8"],
      txt: ["/api/report/txt", `${safeTitle}.txt`, "text/plain;charset=utf-8"],
      docx: ["/api/report/docx", `${safeTitle}.docx`, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
    };
    const selected = formats[format];
    if (!selected) throw new Error("不支持的导出格式。");
    await requestDownload(
      selected[0],
      { results: single.results, use_ai_summary: false },
      selected[1],
      selected[2],
      "当前模块还没有可导出的结果。",
      "模块导出超时，请稍后重试。",
    );
  }

  function decorateToolbar(panel) {
    const header = panel.querySelector(".result-header");
    if (!(header instanceof HTMLElement)) return;
    header.classList.add("ui-v4-document-header");
    const copy = header.querySelector(".copy-result");
    if (copy instanceof HTMLButtonElement) {
      if (cleanText(copy.textContent) === "复制结果") copy.textContent = "复制正文";
      copy.setAttribute("aria-label", "复制当前结果正文");
      copy.setAttribute("title", "复制当前结果正文");
    }
    const group = header.querySelector(".inline-download-group");
    if (group instanceof HTMLElement) {
      group.classList.add("ui-v4-export-group");
      group.setAttribute("aria-label", "导出当前结果");
      const label = group.querySelector(".download-group-label");
      if (label) label.textContent = "导出";
      group.querySelectorAll(".export-result").forEach(button => {
        const format = String(button.dataset.format || "").toLowerCase();
        const name = format === "docx" ? "Word" : format === "md" ? "Markdown" : format.toUpperCase();
        button.setAttribute("aria-label", `下载 ${name} 文件`);
        button.setAttribute("title", `下载 ${name} 文件`);
      });
    }
  }

  function decorateMeta(panel) {
    const meta = panel.querySelector(".result-meta");
    if (!(meta instanceof HTMLElement)) return;
    meta.classList.add("ui-v4-document-meta");
    meta.setAttribute("aria-label", "文档信息");
    meta.querySelectorAll(".meta-pill").forEach(item => {
      const text = cleanText(item.textContent);
      if (!item.classList.contains("danger") && INTERNAL_META_RE.test(text)) {
        item.remove();
        return;
      }
      item.classList.add("ui-v4-document-meta-item");
    });
    meta.hidden = !meta.querySelector(".meta-pill");
  }

  function ensureStatusRail(panel) {
    let rail = panel.querySelector(":scope > .ui-v4-document-status-rail");
    const bars = [panel.querySelector(".review-workflow-bar"), panel.querySelector(".structured-result-bar")].filter(Boolean);
    if (!bars.length) { rail?.remove(); return; }
    if (!(rail instanceof HTMLElement)) {
      rail = document.createElement("div");
      rail.className = "ui-v4-document-status-rail";
      rail.setAttribute("aria-label", "结果状态与复核");
      const meta = panel.querySelector(".result-meta");
      if (meta) meta.insertAdjacentElement("afterend", rail); else panel.prepend(rail);
    }
    bars.forEach(bar => {
      bar.classList.add("ui-v4-document-status-item");
      if (bar.parentElement !== rail) rail.appendChild(bar);
    });
  }

  function tableData(table) {
    const headers = Array.from(table.querySelectorAll("thead th")).map(cell => cleanText(cell.textContent));
    const rows = Array.from(table.querySelectorAll("tbody tr")).map(row => Array.from(row.querySelectorAll("td")).map(cell => cleanText(cell.textContent)));
    return { headers, rows: rows.filter(row => row.some(Boolean)) };
  }

  function statusTone(value) {
    const text = cleanText(value);
    if (/(高风险|严重|逾期|异常|失败|拒绝|未通过|不通过|未达标)/.test(text)) return "danger";
    if (/(待确认|待补充|未确认|未知|待定|部分明确|未完成|不明确|需补充|处理中)/.test(text)) return "pending";
    if (/(已确认|已完成|已通过|正常|低风险)/.test(text)) return "success";
    return "neutral";
  }

  function makeStatus(value) {
    const status = document.createElement("span");
    status.className = "ui-v4-record-status";
    status.dataset.tone = statusTone(value);
    status.textContent = value || "待确认";
    return status;
  }

  function replaceSummaryTable(table, model) {
    if (model.rows.length !== 1 || model.headers.length < 2 || model.headers.length > 8) return false;
    const grid = document.createElement("dl");
    grid.className = "ui-v4-fact-grid";
    model.headers.forEach((header, index) => {
      const value = model.rows[0][index];
      if (!header || !value) return;
      const item = document.createElement("div");
      item.className = "ui-v4-fact-item";
      const term = document.createElement("dt");
      term.textContent = header;
      const description = document.createElement("dd");
      description.textContent = value;
      item.append(term, description);
      grid.appendChild(item);
    });
    if (!grid.children.length) return false;
    table.replaceWith(grid);
    return true;
  }

  function replaceRecordTable(table, model, kind) {
    if (!model.headers.length || !model.rows.length || model.headers.length > 8 || model.rows.length > 30) return false;
    const statusIndex = model.headers.findIndex(header => STATUS_HEADER_RE.test(header));
    const list = document.createElement("div");
    list.className = `ui-v4-record-list ui-v4-record-list-${kind}`;
    list.setAttribute("role", "list");

    model.rows.forEach((row, rowIndex) => {
      const primary = row[0] || `${KIND_LABELS[kind] || "事项"} ${rowIndex + 1}`;
      const record = document.createElement("article");
      record.className = `ui-v4-business-record ui-v4-business-record-${kind}`;
      record.setAttribute("role", "listitem");

      const head = document.createElement("div");
      head.className = "ui-v4-record-head";
      const index = document.createElement("span");
      index.className = "ui-v4-record-index";
      index.textContent = String(rowIndex + 1).padStart(2, "0");
      const title = document.createElement("strong");
      title.className = "ui-v4-record-title";
      title.textContent = primary;
      head.append(index, title);
      if (statusIndex >= 0 && row[statusIndex]) head.appendChild(makeStatus(row[statusIndex]));
      record.appendChild(head);

      const meta = document.createElement("dl");
      meta.className = "ui-v4-record-meta";
      model.headers.forEach((header, columnIndex) => {
        if (columnIndex === 0 || columnIndex === statusIndex) return;
        const value = row[columnIndex];
        if (!header || !value) return;
        const item = document.createElement("div");
        const term = document.createElement("dt");
        term.textContent = header;
        const description = document.createElement("dd");
        description.textContent = value;
        item.append(term, description);
        meta.appendChild(item);
      });
      if (meta.children.length) record.appendChild(meta);
      list.appendChild(record);
    });

    if (!list.children.length) return false;
    table.replaceWith(list);
    return true;
  }

  function decorateTable(table, sectionTitle) {
    if (!(table instanceof HTMLTableElement)) return;
    table.classList.add("ui-v4-document-table");
    if (!table.hasAttribute("aria-label")) table.setAttribute("aria-label", `${sectionTitle || "结果"}表格`);
    table.querySelectorAll("thead th").forEach(cell => cell.setAttribute("scope", "col"));
    if (!table.parentElement?.classList.contains("ui-v4-table-scroll")) {
      const wrap = document.createElement("div");
      wrap.className = "ui-v4-table-scroll";
      wrap.tabIndex = 0;
      wrap.setAttribute("role", "region");
      wrap.setAttribute("aria-label", `${sectionTitle || "结果"}表格，可横向滚动`);
      table.replaceWith(wrap);
      wrap.appendChild(table);
    }
  }

  function upgradeBusinessTables(section, sectionTitle, kind) {
    section.querySelectorAll("table").forEach(table => {
      if (!(table instanceof HTMLTableElement)) return;
      const model = tableData(table);
      if (kind === "summary" && replaceSummaryTable(table, model)) return;
      if (RECORD_KINDS.has(kind) && replaceRecordTable(table, model, kind)) return;
      decorateTable(table, sectionTitle);
    });
  }

  function decorateSection(section, index, module) {
    if (!(section instanceof HTMLElement)) return;
    const title = section.querySelector(".result-section-title h3");
    const titleText = cleanText(title?.textContent) || `第 ${index + 1} 节`;
    const kind = sectionKind(titleText);
    section.dataset.uiV4SectionKind = kind;
    section.classList.add("ui-v4-document-section");
    if (title instanceof HTMLElement) {
      if (!title.id) title.id = `ui-v4-${module}-section-${index + 1}`;
      section.setAttribute("role", "region");
      section.setAttribute("aria-labelledby", title.id);
      const titleRow = title.closest(".result-section-title");
      let badge = titleRow?.querySelector(".ui-v4-section-kind-badge");
      if (kind !== "default") {
        if (!(badge instanceof HTMLElement)) {
          badge = document.createElement("span");
          badge.className = "ui-v4-section-kind-badge";
          titleRow?.appendChild(badge);
        }
        badge.dataset.kind = kind;
        badge.textContent = KIND_LABELS[kind] || "";
      } else badge?.remove();
    }
    upgradeBusinessTables(section, titleText, kind);
  }

  function decorateBody(panel) {
    const body = panel.querySelector(".result-body");
    if (!(body instanceof HTMLElement)) return;
    body.classList.add("ui-v4-document-body");
    const module = moduleFromPanel(panel);
    body.querySelectorAll(":scope > .result-section-card").forEach((section, index) => decorateSection(section, index, module));
  }

  function decorateStreaming(panel) {
    const streaming = panel.querySelector(".streaming-stage, .streaming-content");
    if (!(streaming instanceof HTMLElement)) return;
    streaming.classList.add("ui-v4-document-streaming");
  }

  function decoratePanel(panel) {
    if (!(panel instanceof HTMLElement)) return;
    panel.classList.add("ui-v4-document-result");
    panel.dataset.uiV4DocumentModule = moduleFromPanel(panel);
    panel.dataset.uiV4DocumentState = panel.classList.contains("streaming") ? "loading"
      : panel.classList.contains("empty") ? "empty"
        : panel.querySelector(".meta-pill.danger") || /生成失败|调用异常/.test(cleanText(panel.textContent)) ? "error" : "ready";
    if (panel.classList.contains("empty")) return;
    decorateToolbar(panel);
    decorateMeta(panel);
    ensureStatusRail(panel);
    decorateBody(panel);
    decorateStreaming(panel);
  }

  function sync() { document.querySelectorAll(PANEL_SELECTOR).forEach(decoratePanel); }
  function scheduleResultSync() {
    if (resultSyncScheduled) return;
    resultSyncScheduled = true;
    queueMicrotask(() => queueMicrotask(() => {
      resultSyncScheduled = false;
      sync();
    }));
  }

  function bindActions() {
    if (actionsBound) return;
    actionsBound = true;
    document.addEventListener("click", async event => {
      const copy = event.target.closest?.(".copy-result");
      if (copy) {
        try {
          const single = typeof collectSingleModuleResult === "function" ? collectSingleModuleResult(copy.dataset.key) : null;
          await copyText(single?.content || "");
          if (typeof toast === "function") toast("已复制当前模块结果");
        } catch (_) {
          if (typeof toast === "function") toast("复制失败，请手动选择结果文本复制。");
        }
        return;
      }
      const exportButton = event.target.closest?.(".export-result");
      if (exportButton) {
        try {
          await downloadModuleFile(exportButton.dataset.key, exportButton.dataset.format);
          if (typeof toast === "function") toast(`已开始下载${String(exportButton.dataset.format || "").toUpperCase()}文件`);
        } catch (error) {
          if (typeof toast === "function") toast(error.message || "导出失败，请稍后重试。");
        }
      }
    });

    const downloads = [
      ["downloadMarkdown", "/api/report/markdown", "智链天河运营报告.md", "text/markdown;charset=utf-8"],
      ["downloadTxt", "/api/report/txt", "智链天河运营报告.txt", "text/plain;charset=utf-8"],
      ["downloadDocx", "/api/report/docx", "智链天河运营报告.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
    ];
    downloads.forEach(([id, url, filename, contentType]) => {
      document.getElementById(id)?.addEventListener("click", async event => {
        const button = event.currentTarget;
        try {
          if (typeof setLoading === "function") setLoading(button, true, "导出中...");
          await downloadReportFile(url, filename, contentType);
          if (typeof toast === "function") toast("报告已开始下载");
        } catch (error) {
          if (typeof toast === "function") toast(error.message || "导出失败，请稍后重试。");
        } finally {
          if (typeof setLoading === "function") setLoading(button, false);
        }
      });
    });
  }

  function start() {
    document.body.classList.add("ui-v4-results");
    bindActions();
    sync();
    window.ZHILINK_UI_V4_RUNTIME?.subscribe?.(sync, { immediate: false });
    const resultUpdatedEvent = window.ZHILINK_WORKSPACE_CONTRACTS?.events?.resultUpdated;
    if (resultUpdatedEvent) window.addEventListener(resultUpdatedEvent, scheduleResultSync);
    window.ZHILINK_UI_V4_RESULTS_READY = true;
  }

  window.ZHILINK_RESULTS = Object.freeze({
    copyText,
    downloadTextFile,
    downloadModuleFile,
    downloadReportFile,
    refreshPresentation: sync,
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();