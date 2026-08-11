/* User-facing meeting view: keep provenance internally, hide implementation IDs by default. */
(() => {
  const INTERNAL_REF_RE = /\[(?:MT-\d{2}|MP-\d{2}|MT-C\d{2})\]/g;
  const HIDDEN_SECTIONS = new Set(["自动一致性校验", "输入证据与待确认索引", "证据索引", "AI 建议补充动作"]);
  const EVIDENCE_HEADERS = ["证据编号", "原文证据", "依据编号", "证据引用", "来源编号"];
  let scheduled = false;
  let decorating = false;

  function rawMeeting() {
    return typeof state !== "undefined" ? String(state.results?.meeting || "") : "";
  }
  function splitRow(line) {
    const value = String(line || "").trim();
    if (!value.startsWith("|") || !value.endsWith("|")) return null;
    return value.slice(1, -1).split("|").map(cell => cell.trim());
  }
  function joinRow(cells) {
    return `| ${cells.join(" | ")} |`;
  }
  function stripHiddenSections(markdown) {
    const output = [];
    let hidden = false;
    for (const line of String(markdown || "").split(/\r?\n/)) {
      const heading = line.match(/^##\s+(.+?)\s*$/);
      if (heading) {
        hidden = HIDDEN_SECTIONS.has(heading[1].trim());
        if (hidden) continue;
      }
      if (!hidden) output.push(line);
    }
    return output.join("\n");
  }
  function removeEvidenceColumns(markdown) {
    const output = [];
    let dropIndexes = [];
    let inTable = false;
    for (const line of String(markdown || "").split(/\r?\n/)) {
      const cells = splitRow(line);
      if (!cells) {
        inTable = false;
        dropIndexes = [];
        output.push(line);
        continue;
      }
      if (!inTable) {
        dropIndexes = cells
          .map((cell, index) => EVIDENCE_HEADERS.some(header => cell.includes(header)) ? index : -1)
          .filter(index => index >= 0);
        inTable = true;
      }
      const filtered = dropIndexes.length ? cells.filter((_, index) => !dropIndexes.includes(index)) : cells;
      if (filtered.length) output.push(joinRow(filtered));
    }
    return output.join("\n");
  }
  function normalizeStatuses(markdown) {
    return String(markdown || "")
      .replace(/原文事实/g, "已确认")
      .replace(/已明确/g, "已确认")
      .replace(/部分明确(?:（[^）]*）)?/g, "待确认")
      .replace(/AI\s*建议（未确认）/g, "AI 建议")
      .replace(/待确认（AI\s*建议：[^）]*）/g, "待确认")
      .replace(/^##\s+(?:原文待办事项|待办事项表)\s*$/gm, "## 待办事项");
  }
  function cleanInternalRefs(markdown) {
    return String(markdown || "")
      .replace(INTERNAL_REF_RE, "")
      .replace(/\s+([，。；：！？])/g, "$1")
      .replace(/\[\s*\]/g, "")
      .replace(/[ \t]+$/gm, "")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }
  function sanitizeMeetingMarkdown(markdown) {
    return cleanInternalRefs(normalizeStatuses(removeEvidenceColumns(stripHiddenSections(markdown))));
  }
  function sanitizeReportMarkdown(markdown) {
    return cleanInternalRefs(removeEvidenceColumns(stripHiddenSections(markdown)));
  }

  function sourceItems(markdown) {
    const items = [];
    const seen = new Set();
    let headers = null;
    for (const line of String(markdown || "").split(/\r?\n/)) {
      const cells = splitRow(line);
      if (!cells) {
        headers = null;
        continue;
      }
      if (!headers) {
        headers = cells;
        continue;
      }
      if (cells.every(cell => /^:?-{3,}:?$/.test(cell.replace(/\s+/g, "")))) continue;
      const idIndex = headers.findIndex(cell => cell.includes("证据编号"));
      const sourceIndex = headers.findIndex(cell => cell.includes("来源"));
      const excerptIndex = headers.findIndex(cell => /输入摘录|摘录/.test(cell));
      if (idIndex < 0 || excerptIndex < 0) continue;
      if (!/^(?:MT-\d{2}|MP-\d{2})$/.test(cells[idIndex] || "")) continue;
      const excerpt = String(cells[excerptIndex] || "").trim();
      if (!excerpt || seen.has(excerpt)) continue;
      seen.add(excerpt);
      items.push({ source: String(cells[sourceIndex] || "会议原文").trim(), excerpt });
    }
    return items;
  }
  function pendingItems(markdown) {
    const items = [];
    const seen = new Set();
    for (const line of String(markdown || "").split(/\r?\n/)) {
      if (!/\[MT-C\d{2}\]/.test(line)) continue;
      const text = line
        .replace(/^\s*[-*]?\s*\[\s*\]\s*/, "")
        .replace(INTERNAL_REF_RE, "")
        .replace(/^\s*[-*|]\s*/, "")
        .replace(/\|\s*$/, "")
        .trim();
      if (!text || seen.has(text)) continue;
      seen.add(text);
      items.push(text);
    }
    return items;
  }
  function safe(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function ensureDrawer() {
    if (document.getElementById("meetingSourceDialog")) return;
    const modal = document.createElement("div");
    modal.id = "meetingSourceDialog";
    modal.className = "meeting-source-modal";
    modal.setAttribute("aria-hidden", "true");
    modal.innerHTML = `
      <div class="meeting-source-backdrop" data-close-meeting-sources></div>
      <section class="meeting-source-dialog" role="dialog" aria-modal="true" aria-labelledby="meetingSourceTitle">
        <header><div><span>生成依据</span><h2 id="meetingSourceTitle">会议原文来源</h2><p>展示实际使用的会议原文和待确认问题，不向业务用户暴露内部编号。</p></div><button type="button" class="icon-btn" data-close-meeting-sources aria-label="关闭生成依据">✕</button></header>
        <div id="meetingSourceBody"></div>
      </section>`;
    document.body.appendChild(modal);

    const style = document.createElement("style");
    style.dataset.meetingUserView = "true";
    style.textContent = `
      .meeting-source-modal{display:none;position:fixed;inset:0;z-index:10000}.meeting-source-modal.show{display:block}
      .meeting-source-backdrop{position:absolute;inset:0;background:rgba(15,23,42,.42)}
      .meeting-source-dialog{position:absolute;right:0;top:0;height:100%;width:min(620px,92vw);background:#fff;box-shadow:-18px 0 45px rgba(15,23,42,.18);padding:24px;overflow:auto}
      .meeting-source-dialog header{display:flex;justify-content:space-between;gap:20px;border-bottom:1px solid #e5e7eb;padding-bottom:18px;margin-bottom:18px}.meeting-source-dialog header p{margin:6px 0 0;color:#64748b;line-height:1.6}
      .meeting-source-list{display:grid;gap:12px}.meeting-source-item{padding:14px 16px;border:1px solid #e5e7eb;border-radius:12px;background:#f8fafc}.meeting-source-item strong{display:block;margin-bottom:6px}.meeting-source-item p{margin:0;line-height:1.65;color:#334155}
      .meeting-source-pending{margin-top:22px}.meeting-source-pending li{margin:7px 0;line-height:1.55}
    `;
    document.head.appendChild(style);
  }

  function openSources() {
    ensureDrawer();
    const sources = sourceItems(rawMeeting());
    const pending = pendingItems(rawMeeting());
    const body = document.getElementById("meetingSourceBody");
    body.innerHTML = sources.length
      ? `<div class="meeting-source-list">${sources.map(item => `<article class="meeting-source-item"><strong>${safe(item.source || "会议原文")}</strong><p>${safe(item.excerpt)}</p></article>`).join("")}</div>`
      : '<div class="notice info">当前没有可展开的原文索引，系统仍保留原始会议输入供人工复核。</div>';
    if (pending.length) body.insertAdjacentHTML("beforeend", `<section class="meeting-source-pending"><h3>仍需人工确认</h3><ul>${pending.map(item => `<li>${safe(item)}</li>`).join("")}</ul></section>`);
    const modal = document.getElementById("meetingSourceDialog");
    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
  }
  function closeSources() {
    const modal = document.getElementById("meetingSourceDialog");
    if (!modal) return;
    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");
  }

  function replaceResultBody(panel, markdown) {
    const body = panel?.querySelector(".result-body");
    if (!body || typeof renderStructuredMarkdown !== "function") return;
    const holder = document.createElement("div");
    holder.innerHTML = renderStructuredMarkdown(markdown);
    const next = holder.firstElementChild;
    if (next && next.innerHTML !== body.innerHTML) body.replaceWith(next);
  }

  function decorateMeetingPanel() {
    if (decorating) return;
    const panel = document.getElementById("meetingResult");
    const raw = rawMeeting();
    if (!panel || !raw || panel.classList.contains("streaming")) return;
    decorating = true;
    try {
      replaceResultBody(panel, sanitizeMeetingMarkdown(raw));
      const mode = panel.querySelector(".result-meta .meta-pill");
      if (mode && mode.textContent !== "AI 生成 · 待人工确认") mode.textContent = "AI 生成 · 待人工确认";
      const origin = panel.querySelector(".data-origin-pill");
      if (origin?.textContent.includes("示例生成")) origin.textContent = "示例数据 · 不会保存为正式材料";
      else if (origin?.textContent.includes("旧会话材料")) origin.textContent = "旧会话材料 · 请重新确认后使用";

      const bar = panel.querySelector(".structured-result-bar");
      if (bar && !bar.classList.contains("meeting-user-structure-bar")) {
        bar.className = "structured-result-bar structured-valid meeting-user-structure-bar";
        bar.innerHTML = '<div><strong>已完成结构检查</strong><small>事实、待确认项和 AI 建议已区分，请人工复核后归档。</small></div>';
      }
      const actions = panel.querySelector(".result-actions");
      if (actions && !actions.querySelector("[data-open-meeting-sources]")) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "inline-action";
        button.dataset.openMeetingSources = "true";
        button.textContent = "查看生成依据";
        actions.appendChild(button);
      }
    } finally {
      decorating = false;
    }
  }

  function scheduleDecorate() {
    if (scheduled) return;
    scheduled = true;
    queueMicrotask(() => {
      scheduled = false;
      decorateMeetingPanel();
    });
  }

  function installExportGuards() {
    if (typeof collectSingleModuleResult === "function") {
      const originalCollectSingle = collectSingleModuleResult;
      collectSingleModuleResult = function userFacingSingleExport(key) {
        const result = originalCollectSingle.apply(this, arguments);
        if (key !== "meeting" && key !== "report") return result;
        const content = key === "meeting" ? sanitizeMeetingMarkdown(result.content) : sanitizeReportMarkdown(result.content);
        return { ...result, content, results: { ...result.results, [result.title]: content } };
      };
    }
    if (typeof downloadReportFile === "function") {
      const originalDownloadReport = downloadReportFile;
      downloadReportFile = function userFacingReportExport() {
        const currentCollector = collectResultsForReport;
        collectResultsForReport = function sanitizedResultsForExport(includeAiSummary = false) {
          const results = currentCollector(includeAiSummary);
          const next = { ...results };
          if (next["会议纪要"]) next["会议纪要"] = sanitizeMeetingMarkdown(next["会议纪要"]);
          if (next["AI整合报告"]) next["AI整合报告"] = sanitizeReportMarkdown(next["AI整合报告"]);
          return next;
        };
        try {
          return originalDownloadReport.apply(this, arguments);
        } finally {
          collectResultsForReport = currentCollector;
        }
      };
    }
  }

  function installInteractions() {
    document.addEventListener("click", event => {
      if (event.target.closest("[data-open-meeting-sources]")) {
        event.preventDefault();
        event.stopPropagation();
        openSources();
        return;
      }
      if (event.target.closest("[data-close-meeting-sources]")) {
        closeSources();
        return;
      }
      if (event.target.closest('.copy-result[data-key="meeting"]')) {
        event.preventDefault();
        event.stopImmediatePropagation();
        Promise.resolve(copyText(sanitizeMeetingMarkdown(rawMeeting())))
          .then(() => toast("已复制会议纪要"))
          .catch(() => toast("复制失败，请手动选择会议纪要文本复制。"));
      }
    }, true);
    document.addEventListener("keydown", event => {
      if (event.key === "Escape") closeSources();
    });
  }

  window.addEventListener("zhilink:result-updated", event => {
    const key = event.detail?.key;
    if (key === "meeting") scheduleDecorate();
    if (key === "report" && event.detail?.content) {
      queueMicrotask(() => replaceResultBody(document.getElementById("reportResult"), sanitizeReportMarkdown(event.detail.content)));
    }
  });
  window.addEventListener("zhilink:structured-updated", event => {
    if (event.detail?.module === "meeting") scheduleDecorate();
  });
  window.addEventListener("zhilink:review-updated", event => {
    if (event.detail?.module === "meeting") scheduleDecorate();
  });

  ensureDrawer();
  installExportGuards();
  installInteractions();
  scheduleDecorate();

  window.ZHILINK_MEETING_USER_VIEW = { sanitize: sanitizeMeetingMarkdown, sources: sourceItems };
  window.ZHILINK_MEETING_USER_VIEW_READY = true;
})();
