/* Keep example and legacy session data out of the formal enterprise workspace. */
(() => {
  const RESULT_KEYS = ["profile", "meeting", "contract", "policy", "match", "landing"];
  const RESULT_TITLES = {
    profile: "企业档案", meeting: "会议纪要", contract: "合同审阅", policy: "政策准备",
    match: "供需协作", landing: "实施计划", report: "运营报告",
  };
  const INPUT_MODULES = {
    profileName: "profile", profileIndustry: "profile", profileLocation: "profile", profileScale: "profile",
    profileStage: "profile", profileRole: "profile", profileDemands: "profile",
    meetingInput: "meeting", contractInput: "contract", policyDemand: "policy",
    offerInput: "match", needInput: "match", targetInput: "match", scenarioInput: "match",
    pilotScene: "landing", userRoles: "landing", dataScope: "landing", deployment: "landing",
    pilotPeriod: "landing", reviewMode: "landing",
  };
  const EXAMPLE_CONTEXT_STORAGE = "zhilian_example_contexts_v1";
  const RESULTS_STORAGE = "zhilian_results";
  const META_STORAGE = "zhilian_meta";
  const CURRENT_PROJECT_STORAGE = "zhilian_current_project_v1";
  const FORMAL_ORIGINS = new Set(["user", "project", "imported"]);
  const PENDING_PATTERN = /(待确认|需确认|人工确认|尚未明确|未明确|待补充|待核实|需核实)/;

  let started = false;
  let bootstrapObserver = null;
  let refreshTimer = null;

  function readJson(raw, fallback) {
    try { return raw ? JSON.parse(raw) : fallback; } catch (_) { return fallback; }
  }

  function appState() {
    return typeof state !== "undefined" ? state : null;
  }

  function examples() {
    return typeof exampleScenarios !== "undefined" ? exampleScenarios : {};
  }

  function contexts() {
    return readJson(sessionStorage.getItem(EXAMPLE_CONTEXT_STORAGE), {});
  }

  function saveContexts(value) {
    sessionStorage.setItem(EXAMPLE_CONTEXT_STORAGE, JSON.stringify(value || {}));
  }

  function moduleFromExampleKey(key) {
    const module = String(key || "").split("-", 1)[0];
    return RESULT_KEYS.includes(module) ? module : "";
  }

  function exampleMatchesCurrentInput(exampleKey) {
    const example = examples()[exampleKey];
    if (!example) return false;
    return Object.entries(example.fields || {}).every(([id, value]) => {
      const element = document.getElementById(id);
      return Boolean(element) && String(element.value || "") === String(value || "");
    });
  }

  function inferLegacyOrigin(key) {
    const marked = contexts()[key];
    if (marked?.exampleKey && exampleMatchesCurrentInput(marked.exampleKey)) return "example";
    const matchedKey = Object.keys(examples()).find(exampleKey => (
      moduleFromExampleKey(exampleKey) === key && exampleMatchesCurrentInput(exampleKey)
    ));
    if (matchedKey) {
      const next = contexts();
      next[key] = { exampleKey: matchedKey, markedAt: new Date().toISOString() };
      saveContexts(next);
      return "example";
    }
    return localStorage.getItem(CURRENT_PROJECT_STORAGE) ? "project" : "legacy";
  }

  function originFor(key) {
    return String(appState()?.meta?.[key]?.origin || "") || inferLegacyOrigin(key);
  }

  function isFormalResult(key) {
    return Boolean(appState()?.results?.[key]) && FORMAL_ORIGINS.has(originFor(key));
  }

  function isolatedKeys() {
    const current = appState();
    return current
      ? Object.keys(current.results || {}).filter(key => current.results[key] && !isFormalResult(key))
      : [];
  }

  function persistMeta() {
    const current = appState();
    if (current) sessionStorage.setItem(META_STORAGE, JSON.stringify(current.meta || {}));
  }

  function migrateExistingResults() {
    const current = appState();
    if (!current) return;
    current.meta ||= {};
    Object.keys(current.results || {}).forEach(key => {
      if (!current.results[key]) return;
      current.meta[key] ||= {};
      if (!current.meta[key].origin) current.meta[key].origin = inferLegacyOrigin(key);
    });
    persistMeta();
  }

  function markExample(exampleKey) {
    const module = moduleFromExampleKey(exampleKey);
    if (!module) return;
    const next = contexts();
    next[module] = { exampleKey, markedAt: new Date().toISOString() };
    saveContexts(next);
  }

  function clearExampleMarker(module) {
    const next = contexts();
    if (!module || !next[module]) return;
    delete next[module];
    saveContexts(next);
  }

  function generationOrigin(key) {
    const marker = contexts()[key];
    return marker?.exampleKey && exampleMatchesCurrentInput(marker.exampleKey) ? "example" : "user";
  }

  function installFunctionGuards() {
    if (window.__ZHILINK_DATA_PROVENANCE_FUNCTIONS) return;
    window.__ZHILINK_DATA_PROVENANCE_FUNCTIONS = true;

    if (typeof window.applyExample === "function") {
      const original = window.applyExample;
      window.applyExample = function provenanceAwareApplyExample(exampleKey) {
        const value = original.apply(this, arguments);
        markExample(exampleKey);
        renderFormalWorkspace();
        return value;
      };
    }

    if (typeof window.setResult === "function") {
      const original = window.setResult;
      window.setResult = function provenanceAwareSetResult(key, result) {
        const value = original.apply(this, arguments);
        const current = appState();
        if (current?.meta?.[key]) {
          const origin = generationOrigin(key);
          current.meta[key].origin = origin;
          const marker = contexts()[key];
          if (origin === "example" && marker?.exampleKey) current.meta[key].example_key = marker.exampleKey;
          else delete current.meta[key].example_key;
          persistMeta();
          if (origin === "example" && typeof toast === "function") {
            toast("已生成示例结果；不会计入正式工作台、待核对事项或运营报告。");
          }
        }
        renderFormalProgress();
        return value;
      };
    }

    window.updateRecentMaterials = renderFormalRecentMaterials;

    if (typeof window.updateProgress === "function") {
      const original = window.updateProgress;
      window.updateProgress = function provenanceAwareUpdateProgress() {
        const value = original.apply(this, arguments);
        renderFormalProgress();
        return value;
      };
    }

    window.collectBaseResults = function collectFormalBaseResults() {
      const current = appState();
      return {
        "企业档案": isFormalResult("profile") ? current.results.profile : "",
        "会议纪要": isFormalResult("meeting") ? current.results.meeting : "",
        "合同审阅": isFormalResult("contract") ? current.results.contract : "",
        "政策准备": isFormalResult("policy") ? current.results.policy : "",
        "供需协作": isFormalResult("match") ? current.results.match : "",
        "实施计划": isFormalResult("landing") ? current.results.landing : "",
      };
    };

    window.collectResultsForReport = function collectFormalResultsForReport(includeAiSummary = false) {
      const base = window.collectBaseResults();
      if (includeAiSummary && isFormalResult("report")) return { "AI整合报告": appState().results.report, ...base };
      return base;
    };
  }

  function formalCount() {
    return RESULT_KEYS.filter(isFormalResult).length;
  }

  function renderFormalProgress() {
    const current = appState();
    if (!current) return;
    const count = formalCount();
    const setText = (id, value) => {
      const element = document.getElementById(id);
      if (element && element.textContent !== value) element.textContent = value;
    };
    setText("generatedCount", `${count} 项`);
    setText("homeGeneratedCount", `${count} 项`);
    setText("reportDoneCount", `${count}/${RESULT_KEYS.length}`);
    document.querySelectorAll(".nav button").forEach(button => {
      const key = button.dataset.section;
      button.classList.toggle("done", key === "report" ? isFormalResult("report") : isFormalResult(key));
    });
    document.querySelectorAll("[data-tool-key]").forEach(card => card.classList.toggle("done", isFormalResult(card.dataset.toolKey)));
    renderFormalRecentMaterials();
    renderFormalWorkspace();
  }

  function renderFormalRecentMaterials() {
    const current = appState();
    const container = document.getElementById("recentMaterials");
    if (!current || !container) return;
    const items = Object.keys(current.results || {})
      .filter(key => isFormalResult(key) && RESULT_TITLES[key])
      .map(key => ({ key, title: RESULT_TITLES[key], time: current.meta?.[key]?.time || "", content: current.results[key] || "" }))
      .sort((a, b) => String(b.time).localeCompare(String(a.time))).slice(0, 5);
    if (!items.length) {
      const isolated = isolatedKeys().length;
      container.className = "recent-list empty";
      container.textContent = isolated
        ? `暂无正式材料。已隔离 ${isolated} 项示例或旧会话材料，可在下方清除。`
        : "暂无正式材料。输入真实业务内容并生成后，这里会显示最近材料。";
      return;
    }
    const safe = value => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
    const html = items.map(item => {
      const timeText = item.time ? new Date(item.time).toLocaleString() : "当前会话";
      const summary = item.content.replace(/[#*_`|>-]/g, "").replace(/\s+/g, " ").trim().slice(0, 90) || "已生成业务材料";
      return `<article class="recent-item"><div class="recent-item-icon">${safe(item.title.slice(0, 1))}</div><div><h4>${safe(item.title)}</h4><p>${safe(timeText)} · ${safe(summary)}</p></div><button class="secondary small" data-goto="${safe(item.key)}" type="button">查看</button></article>`;
    }).join("");
    container.className = "recent-list";
    if (container.innerHTML !== html) container.innerHTML = html;
  }

  function collectFormalPendingItems() {
    const current = appState();
    const seen = new Set();
    const items = [];
    if (!current) return items;
    RESULT_KEYS.forEach(key => {
      if (!isFormalResult(key)) return;
      String(current.results[key] || "").split(/\n+/).forEach(raw => {
        const text = raw.replace(/^[#>*\-\d.、\s]+/, "").replace(/\[[A-Z0-9-]+\]/g, "")
          .replace(/\s+/g, " ").trim();
        if (!text || !PENDING_PATTERN.test(text) || seen.has(text)) return;
        seen.add(text);
        items.push({ key, title: text.slice(0, 90), source: RESULT_TITLES[key] || key });
      });
    });
    return items.slice(0, 6);
  }

  function reviewCounts() {
    let confirmed = 0;
    let pending = 0;
    RESULT_KEYS.forEach(key => {
      if (!isFormalResult(key)) return;
      document.getElementById(`${key}Result`)?.querySelectorAll(".review-workflow-bar strong").forEach(node => {
        const text = node.textContent || "";
        if (/(批准|已确认)/.test(text)) confirmed += 1;
        if (/(待审核|退回|失效|尚未建立)/.test(text)) pending += 1;
      });
    });
    return { confirmed, pending };
  }

  function ensureFormalPanels() {
    const grid = document.getElementById("liveHomeGrid");
    if (!grid) return false;
    if (!document.getElementById("formalPendingPanel")) {
      const pending = document.createElement("section");
      pending.id = "formalPendingPanel";
      pending.className = "live-home-panel formal-pending-panel";
      pending.innerHTML = '<div class="live-panel-head"><div><h3>AI 待人工核对</h3><p>只显示真实业务材料中需要人工确认的内容。</p></div><span id="formalPendingCount">0 项</span></div><div id="formalPendingList" class="live-pending-list"></div>';
      grid.appendChild(pending);
    }
    if (!document.getElementById("formalUsagePanel")) {
      const usage = document.createElement("section");
      usage.id = "formalUsagePanel";
      usage.className = "live-home-panel live-usage-panel formal-usage-panel";
      usage.innerHTML = '<div class="live-panel-head"><h3>正式工作台数据</h3><span>真实数据</span></div><div id="formalMetrics" class="live-metrics"></div><p id="formalUsageNote" class="live-usage-note"></p>';
      grid.appendChild(usage);
    }
    bootstrapObserver?.disconnect();
    bootstrapObserver = null;
    return true;
  }

  function renderIsolationNotice() {
    const grid = document.getElementById("liveHomeGrid");
    if (!grid) return;
    const keys = isolatedKeys();
    let notice = document.getElementById("dataIsolationNotice");
    if (!keys.length) {
      notice?.remove();
      return;
    }
    if (!notice) {
      notice = document.createElement("section");
      notice.id = "dataIsolationNotice";
      notice.className = "data-isolation-notice";
      grid.parentNode.insertBefore(notice, grid);
    }
    const labels = keys.map(key => RESULT_TITLES[key] || key).join("、");
    const html = `<div><strong>已隔离 ${keys.length} 项示例或旧会话材料</strong><p>${labels} 不计入待核对、统计和正式报告。需要正式使用时，请替换为真实业务输入并重新生成。</p></div><button id="clearIsolatedResults" type="button">清除隔离材料</button>`;
    if (notice.innerHTML !== html) notice.innerHTML = html;
  }

  function decorateResultOrigins() {
    const current = appState();
    if (!current) return;
    Object.keys(current.results || {}).forEach(key => {
      if (!current.results[key]) return;
      const panel = document.getElementById(`${key}Result`);
      if (!panel) return;
      const origin = originFor(key);
      panel.dataset.resultOrigin = origin;
      const existing = panel.querySelector(".data-origin-pill");
      if (FORMAL_ORIGINS.has(origin)) {
        existing?.remove();
        return;
      }
      const text = origin === "example" ? "示例生成 · 不计入正式工作台" : "旧会话材料 · 已隔离";
      const className = `meta-pill data-origin-pill ${origin === "example" ? "example" : "legacy"}`;
      if (existing && existing.textContent === text && existing.className === className) return;
      existing?.remove();
      const meta = panel.querySelector(".result-meta");
      if (!meta) return;
      const badge = document.createElement("span");
      badge.className = className;
      badge.textContent = text;
      meta.prepend(badge);
    });
  }

  function renderFormalWorkspace() {
    decorateResultOrigins();
    if (!ensureFormalPanels()) return;
    const pendingItems = collectFormalPendingItems();
    const count = document.getElementById("formalPendingCount");
    if (count) count.textContent = `${pendingItems.length} 项`;
    const list = document.getElementById("formalPendingList");
    if (list) {
      const safe = value => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
      const html = pendingItems.length
        ? pendingItems.map(item => `<article class="live-pending-item formal-pending-item"><span class="live-pending-icon">!</span><div><strong>${safe(item.title)}</strong><small>${safe(item.source)} · 请核对原始材料后使用</small></div><button type="button" data-formal-goto="${safe(item.key)}">前往核对</button></article>`).join("")
        : '<p class="live-panel-empty">当前正式生成结果中没有识别到待人工核对事项。</p>';
      if (list.innerHTML !== html) list.innerHTML = html;
    }
    const reviews = reviewCounts();
    const projectCount = Number(document.getElementById("liveSidebarProjectCount")?.textContent || 0) || 0;
    const metrics = document.getElementById("formalMetrics");
    const metricsHtml = `<div class="live-metric"><strong>${formalCount()}</strong><span>正式材料</span></div><div class="live-metric"><strong>${projectCount}</strong><span>可访问项目</span></div><div class="live-metric"><strong>${reviews.confirmed}</strong><span>已确认 / 批准</span></div><div class="live-metric"><strong>${reviews.pending}</strong><span>待复核状态</span></div>`;
    if (metrics && metrics.innerHTML !== metricsHtml) metrics.innerHTML = metricsHtml;
    const project = readJson(localStorage.getItem(CURRENT_PROJECT_STORAGE), null);
    const note = document.getElementById("formalUsageNote");
    const noteText = project
      ? `当前项目：${project.name} · v${project.lock_version}${project.status === "archived" ? " · 已归档" : ""}`
      : "当前未打开持久化项目。只有真实生成结果会进入正式统计。";
    if (note && note.textContent !== noteText) note.textContent = noteText;
    renderIsolationNotice();
  }

  function clearIsolatedResults() {
    const current = appState();
    if (!current) return;
    const keys = isolatedKeys();
    keys.forEach(key => {
      delete current.results[key];
      delete current.meta[key];
      if (typeof window.showResult === "function") window.showResult(key, {});
    });
    sessionStorage.setItem(RESULTS_STORAGE, JSON.stringify(current.results || {}));
    sessionStorage.setItem(META_STORAGE, JSON.stringify(current.meta || {}));
    saveContexts({});
    if (typeof toast === "function") toast(`已清除 ${keys.length} 项示例或旧会话材料。`);
    renderFormalProgress();
  }

  function bindEvents() {
    document.addEventListener("input", event => {
      const module = INPUT_MODULES[event.target?.id];
      if (module && event.isTrusted) clearExampleMarker(module);
    }, true);
    document.addEventListener("click", event => {
      const goto = event.target.closest("[data-formal-goto]");
      if (goto && typeof window.go === "function") window.go(goto.dataset.formalGoto);
      if (event.target.closest("#clearIsolatedResults")) clearIsolatedResults();
      const projectSave = event.target.closest("#createProjectButton, #saveProjectButton");
      if (projectSave && isolatedKeys().length) {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (typeof toast === "function") toast("当前包含示例或旧会话材料。请先清除隔离材料，再保存正式项目。");
      }
    }, true);
    ["zhilink:account-ready", "zhilink:workspace-state-change"].forEach(name => {
      window.addEventListener(name, renderFormalWorkspace);
      document.addEventListener(name, renderFormalWorkspace);
    });
    window.addEventListener("storage", renderFormalWorkspace);
  }

  function waitForHomePanels() {
    if (ensureFormalPanels()) {
      renderFormalWorkspace();
      return;
    }
    if (bootstrapObserver || !document.body) return;
    bootstrapObserver = new MutationObserver(() => {
      if (ensureFormalPanels()) renderFormalWorkspace();
    });
    bootstrapObserver.observe(document.body, { childList: true, subtree: true });
    window.setTimeout(() => {
      bootstrapObserver?.disconnect();
      bootstrapObserver = null;
      renderFormalWorkspace();
    }, 5000);
  }

  function start() {
    if (started) return;
    if (typeof window.setResult !== "function" || !appState()) {
      window.setTimeout(start, 40);
      return;
    }
    started = true;
    installFunctionGuards();
    migrateExistingResults();
    bindEvents();
    renderFormalProgress();
    waitForHomePanels();
    refreshTimer = window.setInterval(renderFormalWorkspace, 30000);
    window.addEventListener("beforeunload", () => window.clearInterval(refreshTimer), { once: true });
    window.ZHILINK_DATA_PROVENANCE_READY = true;
    window.dispatchEvent(new CustomEvent("zhilink:data-provenance-ready"));
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else window.setTimeout(start, 0);
  window.addEventListener("zhilink:ui-v3-ready", start, { once: true });
})();
