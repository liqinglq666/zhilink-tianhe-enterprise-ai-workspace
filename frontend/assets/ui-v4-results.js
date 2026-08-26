/* UI V4 results: owns result presentation chrome, copy/export actions and document utilities. */
(() => {
  const PANEL_SELECTOR = ".result-panel";
  const REQUEST_TIMEOUT_MS = 180000;
  const INTERNAL_META_RE = /(AI\s*模型|流式模式|模型模式|本地报告模式|含证据索引|本地规则预检|连接超时|生成超时|请求已发送|服务端协调)/i;
  const KIND_RULES = [
    ["pending", /(待确认|待补充|需确认|未确认|信息缺口|未知事项|待核实)/],
    ["risk", /(风险|问题|注意事项|合规|警示|隐患|异常)/],
    ["decision", /(关键决策|会议决策|决定事项|已确认事项|核心结论|结论)/],
    ["action", /(待办|行动|下一步|执行|任务|实施|跟进|建议动作|工作安排)/],
    ["evidence", /(生成依据|来源|证据|参考材料|政策依据|原文依据)/],
    ["summary", /(摘要|概览|总结|总体判断|一句话|核心信息)/],
  ];
  const KIND_LABELS = { summary: "摘要", decision: "决策", action: "执行", risk: "风险", pending: "待确认", evidence: "依据" };
  let actionsBound = false;

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

  function activeRequestConfig() {
    return window.ZHILINK_MODEL_CONFIG?.getRequestConfig?.() || { api_key: "", base_url: "", model: "", temperature: 0.35 };
  }

  async function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(String(text || ""));
      return;
    }
    const textarea = document.createElement("textarea");
    textarea.value = String(text || "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
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
        const text = await response.text();
        let detail = text;
        try { detail = JSON.parse(text).detail || text; } catch (_) {}
        throw new Error(detail);
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
      throw error;
    } finally {
      clearTimeout(timer);
    }
  }

  async function downloadReportFile(url, filename, contentType) {
    if (typeof collectResultsForReport !== "function") throw new Error("结果汇总模块未就绪。");
    const results = collectResultsForReport(true);
    await requestDownload(
      url,
      { config: activeRequestConfig(), results, use_ai_summary: false },
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
      { config: activeRequestConfig(), results: single.results, use_ai_summary: false },
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

  function decorateTable(table, sectionTitle) {
    if (!(table instanceof HTMLTableElement)) return;
    table.classList.add("ui-v4-document-table");
    if (!table.hasAttribute("aria-label")) table.setAttribute("aria-label", `${sectionTitle || "结果"}表格`);
    table.querySelectorAll("thead th").forEach(cell => cell.setAttribute("scope", "col"));
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
    section.querySelectorAll("table").forEach(table => decorateTable(table, titleText));
  }

  function decorateBody(panel) {
    const body = panel.querySelector(".result-body");
    if (!(body instanceof HTMLElement)) return;
    body.classList.add("ui-v4-document-body");
    const module = moduleFromPanel(panel);
    body.querySelectorAll(":scope > .result-section-card").forEach((section, index) => decorateSection(section, index, module));
  }

  function decorateStreaming(panel) {
    const streaming = panel.querySelector(".streaming-content");
    if (!(streaming instanceof HTMLElement)) return;
    streaming.classList.add("ui-v4-document-streaming");
    streaming.setAttribute("aria-live", "polite");
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
          if (typeof toast === "function") toast(error.message || String(error));
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
          if (typeof toast === "function") toast(error.message || String(error));
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
