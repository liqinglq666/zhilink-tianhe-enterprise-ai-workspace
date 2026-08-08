/* User-facing meeting result view: keep provenance internally, hide implementation IDs by default. */
(() => {
  const MODULE = "meeting";
  const INTERNAL_REF_RE = /\[(?:MT-\d{2}|MP-\d{2}|MT-C\d{2})\]/g;
  const INTERNAL_SECTION_TITLES = new Set([
    "自动一致性校验",
    "输入证据与待确认索引",
    "证据索引",
    "AI 建议补充动作",
  ]);
  const EVIDENCE_HEADERS = ["证据编号", "原文证据", "依据编号", "证据引用", "来源编号"];
  let observer = null;
  let decorating = false;

  function rawMeeting() {
    return typeof state !== "undefined" ? String(state.results?.meeting || "") : "";
  }

  function stripInternalSections(markdown) {
    const lines = String(markdown || "").split(/\r?\n/);
    const output = [];
    let skip = false;
    for (const line of lines) {
      const match = line.match(/^##\s+(.+?)\s*$/);
      if (match) {
        const title = match[1].trim();
        skip = INTERNAL_SECTION_TITLES.has(title);
        if (skip) continue;
      }
      if (!skip) output.push(line);
    }
    return output.join("\n");
  }

  function splitTableRow(line) {
    const trimmed = String(line || "").trim();
    if (!trimmed.startsWith("|") || !trimmed.endsWith("|")) return null;
    return trimmed.slice(1, -1).split("|").map(cell => cell.trim());
  }

  function joinTableRow(cells) {
    return `| ${cells.join(" | ")} |`;
  }

  function isSeparatorRow(cells) {
    return Boolean(cells?.length) && cells.every(cell => /^:?-{3,}:?$/.test(cell.replace(/\s+/g, "")));
  }

  function removeEvidenceColumns(markdown) {
    const lines = String(markdown || "").split(/\r?\n/);
    const output = [];
    let drop = [];
    let inTable = false;

    for (const line of lines) {
      const cells = splitTableRow(line);
      if (!cells) {
        inTable = false;
        drop = [];
        output.push(line);
        continue;
      }

      if (!inTable) {
        drop = cells
          .map((cell, index) => EVIDENCE_HEADERS.some(header => cell.includes(header)) ? index : -1)
          .filter(index => index >= 0);
        inTable = true;
      }

      const filtered = drop.length ? cells.filter((_, index) => !drop.includes(index)) : cells;
      if (!filtered.length) continue;
      output.push(joinTableRow(filtered));
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
      .replace(/^##\s+原文待办事项\s*$/gm, "## 待办事项")
      .replace(/^##\s+待办事项表\s*$/gm, "## 待办事项");
  }

  function cleanDanglingText(markdown) {
    return String(markdown || "")
      .replace(INTERNAL_REF_RE, "")
      .replace(/\s+([，。；：！？])/g, "$1")
      .replace(/\[\s*\]/g, "")
      .replace(/[ \t]+$/gm, "")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  function sanitizeMeetingMarkdown(markdown) {
    return cleanDanglingText(normalizeStatuses(removeEvidenceColumns(stripInternalSections(markdown))));
  }

  function sanitizeReportMarkdown(markdown) {
    return cleanDanglingText(removeEvidenceColumns(stripInternalSections(markdown)));
  }

  function evidenceSources(markdown) {
    const lines = String(markdown || "").split(/\r?\n/);
    const items = [];
    const seen = new Set();
    let columns = null;

    for (const line of lines) {
      const cells = splitTableRow(line);
      if (!cells) {
        columns = null;
        continue;
      }
      if (!columns) {
        columns = cells;
        continue;
      }
      if (isSeparatorRow(cells)) continue;

      const idIndex = columns.findIndex(cell => /证据编号/.test(cell));
      const sourceIndex = columns.findIndex(cell => /来源/.test(cell));
      const fieldIndex = columns.findIndex(cell => /字段/.test(cell));
      const excerptIndex = columns.findIndex(cell => /输入摘录|摘录/.test(cell));
      if (idIndex < 0 || excerptIndex < 0) continue;
      if (!/^(?:MT-\d{2}|MP-\d{2})$/.test(cells[idIndex] || "")) continue;

      const excerpt = String(cells[excerptIndex] || "").trim();
      if (!excerpt || seen.has(excerpt)) continue;
      seen.add(excerpt);
      items.push({
        source: String(cells[sourceIndex] || "会议原文").trim(),
        field: String(cells[fieldIndex] || "").trim(),
        excerpt,
      });
    }
    return items;
  }

  function pendingQuestions(markdown) {
    const items = [];
    const seen = new Set();
    String(markdown || "").split(/\r?\n/).forEach(line => {
      if (!/MT-C\d{2}/.test(line)) return;
      const text = line
        .replace(/^\s*[-*]?\s*\[\s*\]\s*/, "")
        .replace(INTERNAL_REF_RE, "")
        .replace(/^\s*[-*]\s*/, "")
        .trim();
      if (!text || seen.has(text)) return;
      seen.add(text);
      items.push(text);
    });
    return items;
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function ensureSourceDialog() {
    if (document.getElementById("meetingSourceDialog")) return;
    const wrapper = document.createElement("div");
    wrapper.id = "meetingSourceDialog";
    wrapper.className = "meeting-source-modal";
    wrapper.setAttribute("aria-hidden", "true");
    wrapper.innerHTML = `
      <div class="meeting-source-backdrop" data-close-meeting-sources></div>
      <section class="meeting-source-dialog" role="dialog" aria-modal="true" aria-labelledby="meetingSourceTitle">
        <header>
          <div><span>生成依据</span><h2 id="meetingSourceTitle">会议原文来源</h2><p>这里展示系统实际使用的会议原文和待确认问题。内部编号不会展示给业务用户。</p></div>
          <button type="button" class="icon-btn" data-close-meeting-sources aria-label="关闭生成依据">✕</button>
        </header>
        <div id="meetingSourceBody" class="meeting-source-body"></div>
      </section>`;
    document.body.appendChild(wrapper);

    const style = document.createElement("style");
    style.dataset.meetingUserView = "true";
    style.textContent = `
      .meeting-source-modal{display:none;position:fixed;inset:0;z-index:10000}.meeting-source-modal.show{display:block}
      .meeting-source-backdrop{position:absolute;inset:0;background:rgba(15,23,42,.42)}
      .meeting-source-dialog{position:absolute;right:0;top:0;height:100%;width:min(620px,92vw);background:#fff;box-shadow:-18px 0 45px rgba(15,23,42,.18);padding:24px;overflow:auto}
      .meeting-source-dialog header{display:flex;justify-content:space-between;gap:20px;border-bottom:1px solid #e5e7eb;padding-bottom:18px;margin-bottom:18px}
      .meeting-source-dialog header span{font-size:12px;color:#64748b}.meeting-source-dialog header h2{margin:4px 0 6px}.meeting-source-dialog header p{margin:0;color:#64748b;line-height:1.6}
      .meeting-source-list{display:grid;gap:12px}.meeting-source-item{padding:14px 16px;border:1px solid #e5e7eb;border-radius:12px;background:#f8fafc}
      .meeting-source-item strong{display:block;margin-bottom:6px}.meeting-source-item p{margin:0;line-height:1.65;color:#334155}.meeting-source-item small{display:block;margin-top:6px;color:#64748b}
      .meeting-source-pending{margin-top:22px}.meeting-source-pending h3{margin-bottom:10px}.meeting-source-pending li{margin:7px 0;line-height:1.55}
      #meetingResult .meeting-user-structure-bar small{line-height:1.5}
    `;
    document.head.appendChild(style);
  }

  function openSources() {
    ensureSourceDialog();
    const raw = rawMeeting();
    const sources = evidenceSources(raw);
    const pending = pendingQuestions(raw);
    const body = document.getElementById("meetingSourceBody");
    body.innerHTML = sources.length
      ? `<div class="meeting-source-list">${sources.map(item => `
          <article class="meeting-source-item">
            <strong>${escapeHtml(item.source || "会议原文")}</strong>
            <p>${escapeHtml(item.excerpt)}</p>
            ${item.field ? `<small>${escapeHtml(item.field)}</small>` : ""}
          </article>`).join("")}</div>`
      : '<div class="notice info">当前结果没有可展开的原文索引，但系统仍会保留原始会议输入用于人工复核。</div>';
    if (pending.length) {
      body.insertAdjacentHTML("beforeend", `<section class="meeting-source-pending"><h3>仍需人工确认</h3><ul>${pending.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul></section>`);
    }
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

  function replaceUserBody(panel, raw) {
    const body = panel.querySelector(":scope > .result-body");
    if (!body || typeof renderStructuredMarkdown !== "function") return;
    const html = renderStructuredMarkdown(sanitizeMeetingMarkdown(raw));
    const holder = document.createElement("div");
    holder.innerHTML = html;
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
      replaceUserBody(panel, raw);

      const mode = panel.querySelector(".result-meta .meta-pill");
      if (mode) mode.textContent = "AI 生成 · 待人工确认";

      const origin = panel.querySelector(".data-origin-pill");
      if (origin?.textContent.includes("示例生成")) origin.textContent = "示例数据 · 不会保存为正式材料";
      if (origin?.textContent.includes("旧会话材料")) origin.textContent = "旧会话材料 · 请重新确认后使用";

      const bar = panel.querySelector(".structured-result-bar");
      if (bar) {
        bar.className = "structured-result-bar structured-valid meeting-user-structure-bar";
        bar.innerHTML = `
          <div><strong>已完成结构检查</strong><small>事实、待确认项和 AI 建议已区分，请人工复核后归档。</small></div>
          <button class="inline-action" type="button" data-open-meeting-sources>查看生成依据</button>`;
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

  function installDisplayGuard() {
    if (typeof showResult === "function" && !window.__ZHILINK_MEETING_USER_SHOW_RESULT) {
      window.__ZHILINK_MEETING_USER_SHOW_RESULT = true;
      const original = showResult;
      showResult = function meetingUserShowResult(key, result) {
        const value = original.apply(this, arguments);
        if (key === MODULE) queueMicrotask(decorateMeetingPanel);
        if (key === "report" && result?.content) {
          const panel = document.getElementById("reportResult");
          const body = panel?.querySelector(":scope > .result-body");
          if (body && typeof renderStructuredMarkdown === "function") {
            const holder = document.createElement("div");
            holder.innerHTML = renderStructuredMarkdown(sanitizeReportMarkdown(result.content));
            if (holder.firstElementChild) body.replaceWith(holder.firstElementChild);
          }
        }
        return value;
      };
    }

    if (typeof setResult === "function" && !window.__ZHILINK_MEETING_USER_SET_RESULT) {
      window.__ZHILINK_MEETING_USER_SET_RESULT = true;
      const original = setResult;
      setResult = function meetingUserSetResult(key, result) {
        const next = key === MODULE && result ? { ...result, mode: "AI 生成 · 待人工确认" } : result;
        const value = original.call(this, key, next);
        if (key === MODULE) queueMicrotask(decorateMeetingPanel);
        return value;
      };
    }
  }

  function installExportGuard() {
    if (typeof collectSingleModuleResult === "function" && !window.__ZHILINK_MEETING_USER_SINGLE_EXPORT) {
      window.__ZHILINK_MEETING_USER_SINGLE_EXPORT = true;
      const original = collectSingleModuleResult;
      collectSingleModuleResult = function meetingUserSingleExport(key) {
        const result = original.apply(this, arguments);
        if (key === MODULE) {
          const content = sanitizeMeetingMarkdown(result.content);
          return { ...result, content, results: { ...result.results, [result.title]: content } };
        }
        if (key === "report") {
          const content = sanitizeReportMarkdown(result.content);
          return { ...result, content, results: { ...result.results, [result.title]: content } };
        }
        return result;
      };
    }

    if (typeof downloadReportFile === "function" && !window.__ZHILINK_MEETING_USER_REPORT_EXPORT) {
      window.__ZHILINK_MEETING_USER_REPORT_EXPORT = true;
      const originalDownload = downloadReportFile;
      downloadReportFile = function meetingUserReportExport() {
        const currentCollector = collectResultsForReport;
        collectResultsForReport = function sanitizedResultsForExport(includeAiSummary = false) {
          const results = currentCollector(includeAiSummary);
          const next = { ...results };
          if (next["会议纪要"]) next["会议纪要"] = sanitizeMeetingMarkdown(next["会议纪要"]);
          if (next["AI整合报告"]) next["AI整合报告"] = sanitizeReportMarkdown(next["AI整合报告"]);
          return next;
        };
        try {
          return originalDownload.apply(this, arguments);
        } finally {
          collectResultsForReport = currentCollector;
        }
      };
    }
  }

  function installClicks() {
    document.addEventListener("click", event => {
      const open = event.target.closest("[data-open-meeting-sources]");
      if (open) {
        event.preventDefault();
        event.stopPropagation();
        openSources();
        return;
      }
      if (event.target.closest("[data-close-meeting-sources]")) {
        closeSources();
        return;
      }

      const copy = event.target.closest('.copy-result[data-key="meeting"]');
      if (copy) {
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

  function startObserver() {
    const panel = document.getElementById("meetingResult");
    if (!panel || observer) return;
    observer = new MutationObserver(() => {
      if (!decorating) setTimeout(decorateMeetingPanel, 0);
    });
    observer.observe(panel, { childList: true, subtree: true, characterData: true });
  }

  ensureSourceDialog();
  installDisplayGuard();
  installExportGuard();
  installClicks();
  startObserver();
  setTimeout(decorateMeetingPanel, 0);
  setTimeout(decorateMeetingPanel, 600);

  window.ZHILINK_MEETING_USER_VIEW = {
    sanitize: sanitizeMeetingMarkdown,
    sources: evidenceSources,
  };
  window.ZHILINK_MEETING_USER_VIEW_READY = true;
})();
