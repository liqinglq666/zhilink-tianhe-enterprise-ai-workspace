/* Deterministic structured JSON views for generated Markdown. */
(() => {
  const STORAGE_KEY = "zhilian_structured_results_v1";
  const MODULES = ["profile", "meeting", "contract", "policy", "match", "landing", "report"];
  const cache = read(sessionStorage.getItem(STORAGE_KEY), {});
  const pending = new Map();
  let activeModule = "";

  function read(raw, fallback) {
    try { return raw ? JSON.parse(raw) : fallback; } catch (_) { return fallback; }
  }

  function safe(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function saveCache() {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(cache));
  }

  async function sha256(text) {
    if (!window.crypto?.subtle) return "";
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(String(text || "")));
    return Array.from(new Uint8Array(digest), item => item.toString(16).padStart(2, "0")).join("");
  }

  async function convert(module, content) {
    const response = await fetch("/api/structured/convert", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ module, content }),
    });
    const text = await response.text();
    const data = read(text, {});
    if (!response.ok) throw new Error(data.detail || text || "结构化转换失败。");
    cache[module] = data;
    saveCache();
    decorate(module);
    return data;
  }

  async function ensure(module, content) {
    if (!MODULES.includes(module) || !String(content || "").trim()) return null;
    if (pending.has(module)) return pending.get(module);
    const task = (async () => {
      const existing = cache[module];
      const digest = await sha256(content);
      if (existing && digest && existing.source_sha256 === digest) {
        decorate(module);
        return existing;
      }
      return convert(module, content);
    })().catch(error => {
      console.warn("structured conversion unavailable", error);
      return null;
    }).finally(() => pending.delete(module));
    pending.set(module, task);
    return task;
  }

  function injectUi() {
    if (!document.querySelector("link[data-structured-results]")) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = "/assets/structured-results.css";
      link.dataset.structuredResults = "true";
      document.head.appendChild(link);
    }
    if (document.getElementById("structuredResultModal")) return;
    const modal = document.createElement("div");
    modal.id = "structuredResultModal";
    modal.className = "structured-modal";
    modal.setAttribute("aria-hidden", "true");
    modal.innerHTML = `
      <div class="structured-modal-backdrop" data-close-structured></div>
      <section class="structured-dialog" role="dialog" aria-modal="true" aria-labelledby="structuredDialogTitle">
        <header class="structured-dialog-header">
          <div>
            <span class="track">结构化 JSON</span>
            <h2 id="structuredDialogTitle">可验证结果</h2>
            <p>该 JSON 由服务端根据当前 Markdown 确定性生成，不会再次调用模型。</p>
          </div>
          <button class="icon-btn" type="button" data-close-structured aria-label="关闭结构化结果">✕</button>
        </header>
        <div id="structuredValidationCard" class="structured-validation-card"></div>
        <div id="structuredSummary" class="structured-summary"></div>
        <div id="structuredCollections" class="structured-collections"></div>
        <details class="structured-sections" open>
          <summary>章节结构</summary>
          <div id="structuredSectionList"></div>
        </details>
        <details class="structured-raw">
          <summary>原始 JSON</summary>
          <pre id="structuredRawJson"></pre>
        </details>
        <footer class="structured-dialog-footer">
          <button class="secondary" id="copyStructuredJson" type="button">复制 JSON</button>
          <button class="primary" id="downloadStructuredJson" type="button">下载 JSON</button>
        </footer>
      </section>`;
    document.body.appendChild(modal);
  }

  function statusText(data) {
    if (!data) return "正在生成 JSON";
    return data.validation?.valid ? "结构化 JSON 已验证" : "结构化 JSON 需复核";
  }

  function decorate(module) {
    const panel = document.getElementById(`${module}Result`);
    if (!panel || !state.results[module]) return;
    panel.querySelector(".structured-result-bar")?.remove();
    const data = cache[module];
    const bar = document.createElement("div");
    bar.className = `structured-result-bar ${data?.validation?.valid ? "structured-valid" : "structured-warning"}`;
    const warningCount = data?.validation?.warnings?.length || 0;
    bar.innerHTML = `
      <div>
        <strong>${safe(statusText(data))}</strong>
        <small>${data ? `Schema ${safe(data.schema_version)} · ${data.validation.section_count} 个章节 · ${data.evidence_ids.length} 个证据编号${warningCount ? ` · ${warningCount} 条告警` : ""}` : "正在根据当前结果生成"}</small>
      </div>
      <button class="inline-action" type="button" data-open-structured="${safe(module)}" ${data ? "" : "disabled"}>查看 JSON</button>`;
    const reviewBar = panel.querySelector(".review-workflow-bar");
    if (reviewBar) reviewBar.insertAdjacentElement("afterend", bar);
    else {
      const meta = panel.querySelector(".result-meta");
      if (meta) meta.insertAdjacentElement("afterend", bar);
      else panel.prepend(bar);
    }
  }

  function itemList(title, items) {
    if (!items?.length) return "";
    return `<section><h3>${safe(title)} <span>${items.length}</span></h3><ul>${items.slice(0, 50).map(item =>
      `<li><strong>${safe(item.id)}</strong><p>${safe(item.text)}</p>${item.evidence_ids?.length ? `<small>${item.evidence_ids.map(safe).join(" · ")}</small>` : ""}</li>`
    ).join("")}</ul></section>`;
  }

  function render(data) {
    const valid = Boolean(data.validation?.valid);
    const warnings = data.validation?.warnings || [];
    document.getElementById("structuredDialogTitle").textContent = `${resultTitles[activeModule] || data.title} · 结构化 JSON`;
    document.getElementById("structuredValidationCard").innerHTML = `
      <div><strong>${valid ? "Schema 校验通过" : "需要人工复核"}</strong>
      <span>SHA-256 ${safe(data.source_sha256.slice(0, 16))}…</span></div>
      ${warnings.length ? `<ul>${warnings.map(item => `<li>${safe(item)}</li>`).join("")}</ul>` : "<p>章节、字段和内容哈希均已生成。</p>"}`;
    document.getElementById("structuredSummary").innerHTML = `
      <span>一句话结论</span><p>${safe(data.summary || "未识别")}</p>
      <div><strong>${data.validation.section_count}</strong><small>章节</small>
      <strong>${data.validation.evidence_reference_count}</strong><small>证据编号</small>
      <strong>${data.validation.pending_confirmation_count}</strong><small>待确认项</small></div>`;
    document.getElementById("structuredCollections").innerHTML =
      itemList("输入事实", data.facts) +
      itemList("AI 推断", data.inferences) +
      itemList("风险", data.risks) +
      itemList("建议动作", data.actions) +
      itemList("待确认信息", data.pending_confirmations);
    document.getElementById("structuredSectionList").innerHTML = (data.sections || []).map(section => `
      <article>
        <header><strong>${safe(section.id)} · ${safe(section.title)}</strong><span>${safe(section.kind)}</span></header>
        ${section.text ? `<p>${safe(section.text)}</p>` : ""}
        ${section.items?.length ? `<ul>${section.items.map(item => `<li>${safe(item)}</li>`).join("")}</ul>` : ""}
        ${section.table ? `<div class="structured-table-wrap"><table><thead><tr>${section.table.columns.map(cell => `<th>${safe(cell)}</th>`).join("")}</tr></thead><tbody>${section.table.rows.map(row => `<tr>${row.map(cell => `<td>${safe(cell)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>` : ""}
        ${section.evidence_ids?.length ? `<small>证据：${section.evidence_ids.map(safe).join(" · ")}</small>` : ""}
      </article>`).join("");
    document.getElementById("structuredRawJson").textContent = JSON.stringify(data, null, 2);
  }

  function open(module) {
    const data = cache[module];
    if (!data) {
      toast("结构化 JSON 仍在生成，请稍后重试。");
      return;
    }
    activeModule = module;
    render(data);
    const modal = document.getElementById("structuredResultModal");
    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
  }

  function close() {
    const modal = document.getElementById("structuredResultModal");
    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");
    activeModule = "";
  }

  async function copyJson() {
    const data = cache[activeModule];
    if (!data) return;
    await copyText(JSON.stringify(data, null, 2));
    toast("已复制结构化 JSON。");
  }

  function downloadJson() {
    const data = cache[activeModule];
    if (!data) return;
    const title = (resultTitles[activeModule] || activeModule).replace(/[\\/:*?"<>|]/g, "_");
    downloadTextFile(`${title}.structured.json`, JSON.stringify(data, null, 2), "application/json;charset=utf-8");
    toast("已开始下载结构化 JSON。");
  }

  const originalShowResult = showResult;
  showResult = function structuredAwareShowResult(key, result) {
    originalShowResult(key, result);
    if (result?.structured) {
      cache[key] = result.structured;
      saveCache();
    }
    Promise.resolve().then(() => ensure(key, result?.content || state.results[key] || ""));
  };

  const originalSetResult = setResult;
  setResult = function structuredAwareSetResult(key, result) {
    originalSetResult(key, result);
    if (result?.structured) {
      cache[key] = result.structured;
      saveCache();
      decorate(key);
    } else {
      ensure(key, result?.content || "");
    }
  };

  injectUi();
  document.addEventListener("click", event => {
    const openButton = event.target.closest("[data-open-structured]");
    if (openButton) { open(openButton.dataset.openStructured); return; }
    if (event.target.closest("[data-close-structured]")) { close(); return; }
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && document.getElementById("structuredResultModal")?.classList.contains("show")) close();
  });
  document.getElementById("copyStructuredJson").addEventListener("click", () => copyJson().catch(error => toast(error.message || String(error))));
  document.getElementById("downloadStructuredJson").addEventListener("click", downloadJson);

  setTimeout(() => {
    MODULES.forEach(module => {
      if (state.results[module]) ensure(module, state.results[module]);
    });
  }, 500);

  window.ZHILINK_STRUCTURED = {
    get: module => cache[module] || null,
    refresh: module => convert(module, state.results[module] || ""),
    schemaVersion: "1.0",
  };
  window.ZHILINK_STRUCTURED_READY = true;
})();
