/* UI V4 results: present generated business output as a readable enterprise document without changing content. */
(() => {
  const VERSION = "20260811.1";
  const { ensureStylesheet } = window.ZHILINK_UI_V4_HELPERS || {};
  if (!ensureStylesheet) throw new Error("UI V4 helpers must load before results.");
  const PANEL_SELECTOR = ".result-panel";
  const KIND_RULES = [
    ["pending", /(待确认|待补充|需确认|未确认|信息缺口|未知事项|待核实)/],
    ["risk", /(风险|问题|注意事项|合规|警示|隐患|异常)/],
    ["decision", /(关键决策|会议决策|决定事项|已确认事项|核心结论|结论)/],
    ["action", /(待办|行动|下一步|执行|任务|实施|跟进|建议动作|工作安排)/],
    ["evidence", /(生成依据|来源|证据|参考材料|政策依据|原文依据)/],
    ["summary", /(摘要|概览|总结|总体判断|一句话|核心信息)/],
  ];
  const KIND_LABELS = { summary: "摘要", decision: "决策", action: "执行", risk: "风险", pending: "待确认", evidence: "依据" };

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
    meta.setAttribute("aria-label", "生成信息");
    meta.querySelectorAll(".meta-pill").forEach(item => item.classList.add("ui-v4-document-meta-item"));
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
  function start() {
    ensureStylesheet("results", `/assets/ui-v4-results.css?v=${VERSION}`);
    document.body.classList.add("ui-v4-results");
    sync();
    window.ZHILINK_UI_V4_RUNTIME?.subscribe?.(sync, { immediate: false });
    window.ZHILINK_UI_V4_RESULTS_READY = true;
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();