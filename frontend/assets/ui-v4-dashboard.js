/* UI V4 dashboard: task-first home workspace and home-only presentation. */
(() => {
  const contracts = window.ZHILINK_WORKSPACE_CONTRACTS;
  const ICONS = window.ZHILINK_UI_V4_ICONS;
  const HELPERS = window.ZHILINK_UI_V4_HELPERS;
  if (!contracts || !ICONS || !HELPERS) throw new Error("Workspace runtime, icons and helpers must load before dashboard.");

  const CURRENT_PROJECT_STORAGE = contracts.storage.currentProject;
  const RESULTS_STORAGE = contracts.storage.results;
  const META_STORAGE = contracts.storage.meta;
  const FORMAL_ORIGINS = new Set(contracts.formalOrigins);
  const RESULT_KEYS = contracts.resultKeys;
  const RESULT_TITLES = contracts.resultTitles;
  const MODULES = contracts.modules;
  const MODULE_ORDER = contracts.moduleOrder;
  const { readJson, setText, escapeHtml: safe } = HELPERS;

  function currentProject() { return readJson(localStorage.getItem(CURRENT_PROJECT_STORAGE), null); }
  function resultState() {
    return {
      results: typeof state !== "undefined" ? state.results || {} : readJson(sessionStorage.getItem(RESULTS_STORAGE), {}),
      meta: typeof state !== "undefined" ? state.meta || {} : readJson(sessionStorage.getItem(META_STORAGE), {}),
    };
  }
  function isFormalResult(key) {
    const external = window.ZHILINK_DATA_PROVENANCE?.isFormalResult;
    if (typeof external === "function") return external(key);
    const { results, meta } = resultState();
    return Boolean(results[key]) && FORMAL_ORIGINS.has(String(meta?.[key]?.origin || ""));
  }
  function projectSignature(project) {
    if (!project) return "none";
    return [project.id || "", project.name || "", project.status || "", project.lock_version || "", project.updated_at || ""].join("|");
  }
  function latestWorkSection() {
    const { results, meta } = resultState();
    const candidates = MODULE_ORDER.filter(key => String(results[key] || "").trim()).map(key => ({ key, time: Date.parse(meta[key]?.time || "") || 0 }));
    candidates.sort((a, b) => b.time - a.time);
    return candidates[0]?.key || MODULE_ORDER[0] || "meeting";
  }
  function gotoSection(section) {
    if (typeof go === "function") go(section);
    else document.querySelector(`.nav button[data-section="${section}"]`)?.click();
  }
  function openProjectManager() { document.getElementById("openProjectManager")?.click(); }
  function scrollToTasks() {
    const toolbar = document.querySelector("#home > .section-toolbar");
    const grid = document.querySelector("#home .module-grid");
    (toolbar || grid)?.scrollIntoView({ behavior: "smooth", block: "start" });
    window.setTimeout(() => grid?.querySelector(".module-card .module-footer button")?.focus(), 300);
  }
  function decorateHomeCards() {
    document.querySelectorAll("#home .module-card[data-tool-key]").forEach(card => {
      const key = card.dataset.toolKey || "";
      const module = MODULES[key];
      const holder = card.querySelector(".module-icon");
      if (holder && module && ICONS[module.icon] && holder.dataset.uiV4Icon !== "true") {
        holder.classList.add("ui-v4-module-icon");
        holder.innerHTML = ICONS[module.icon];
        holder.dataset.uiV4Icon = "true";
      }
      const button = card.querySelector(".module-footer button");
      if (button && button.dataset.uiV4Arrow !== "true") {
        button.insertAdjacentHTML("beforeend", ICONS.arrow);
        button.dataset.uiV4Arrow = "true";
      }
    });
  }
  function collectPendingItems() {
    const items = [];
    const seen = new Set();
    const pattern = /(待确认|需确认|人工确认|尚未明确|未明确|待补充|待核实|需核实)/;
    const { results } = resultState();
    RESULT_KEYS.forEach(key => {
      if (!isFormalResult(key)) return;
      String(results[key] || "").split(/\n+/).forEach(raw => {
        const text = raw.replace(/^[#>*\-\d.、\s]+/, "").replace(/\[[A-Z0-9-]+\]/g, "").replace(/\s+/g, " ").trim();
        if (!text || !pattern.test(text) || seen.has(text)) return;
        seen.add(text);
        items.push({ title: text.slice(0, 70), source: RESULT_TITLES[key] || key });
      });
    });
    RESULT_KEYS.forEach(key => {
      if (!isFormalResult(key)) return;
      document.getElementById(`${key}Result`)?.querySelectorAll(".review-workflow-bar strong").forEach(node => {
        const text = node.textContent.trim();
        if (!/(待审核|退回|失效|尚未建立)/.test(text)) return;
        const title = `${RESULT_TITLES[key] || "材料"}：${text}`;
        if (!seen.has(title)) { seen.add(title); items.push({ title, source: "人工复核" }); }
      });
    });
    return items.slice(0, 4);
  }
  function renderPending() {
    const list = document.getElementById("uiV4PendingList");
    const count = document.getElementById("uiV4PendingCount");
    if (!list || !count) return;
    const items = collectPendingItems();
    setText(count, `${items.length} 项`);
    const html = items.length
      ? items.map(item => `<article class="ui-v4-pending-item"><span class="ui-v4-pending-icon">!</span><div><strong>${safe(item.title)}</strong><small>${safe(item.source)} · 请人工核对后使用</small></div></article>`).join("")
      : '<p class="ui-v4-panel-empty">当前正式材料中没有识别到待确认事项。新材料生成后会自动更新。</p>';
    if (list.innerHTML !== html) list.innerHTML = html;
  }
  function reviewCounts() {
    let confirmed = 0; let pending = 0;
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
  function renderUsage() {
    const metrics = document.getElementById("uiV4Metrics");
    const note = document.getElementById("uiV4UsageNote");
    if (!metrics || !note) return;
    const generated = typeof window.ZHILINK_DATA_PROVENANCE?.formalCount === "function" ? window.ZHILINK_DATA_PROVENANCE.formalCount() : RESULT_KEYS.filter(isFormalResult).length;
    const project = currentProject();
    const reviews = reviewCounts();
    const projectCount = Number(window.ZHILINK_UI_V4_SHELL?.projectCount?.() || 0);
    const html = `<div class="ui-v4-metric"><strong>${generated}</strong><span>正式材料</span></div><div class="ui-v4-metric"><strong>${projectCount}</strong><span>可访问项目</span></div><div class="ui-v4-metric"><strong>${reviews.confirmed}</strong><span>已确认 / 批准</span></div><div class="ui-v4-metric"><strong>${reviews.pending}</strong><span>待复核状态</span></div>`;
    if (metrics.innerHTML !== html) metrics.innerHTML = html;
    setText(note, project ? `当前项目：${project.name} · v${project.lock_version}${project.status === "archived" ? " · 已归档" : ""}` : "当前未打开持久化项目。示例和旧会话材料不会进入正式统计。");
  }
  function decorateHero() {
    const home = document.getElementById("home");
    const hero = home?.querySelector(".hero-card");
    const content = hero?.querySelector(".hero-content");
    const eyebrow = content?.querySelector(".eyebrow");
    const title = content?.querySelector("h3");
    const description = content?.querySelector(":scope > p");
    const actions = content?.querySelector(".button-row");
    if (!hero || !content || !title || !description || !actions) return;
    const project = currentProject();
    const signature = projectSignature(project);
    if (hero.dataset.uiV4WorkSignature === signature) return;
    hero.dataset.uiV4WorkSignature = signature;
    setText(eyebrow, project ? "当前工作" : "工作首页");
    if (project) {
      setText(title, project.name || "当前项目");
      const updated = project.updated_at ? new Date(project.updated_at).toLocaleString([], { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "";
      const status = project.status === "archived" ? "已归档" : "进行中";
      setText(description, `项目 ${status} · v${project.lock_version || 1}${updated ? ` · 最近更新 ${updated}` : ""}。继续处理最近的业务材料，或进入项目管理查看版本。`);
      actions.innerHTML = `<button id="uiV4ContinueWork" class="primary" type="button">继续工作</button><button id="uiV4ProjectDetails" class="secondary" type="button">项目与版本</button><button id="uiV4NewTask" class="ghost" type="button">新建任务</button>`;
      document.getElementById("uiV4ContinueWork")?.addEventListener("click", () => gotoSection(latestWorkSection()));
      document.getElementById("uiV4ProjectDetails")?.addEventListener("click", openProjectManager);
      document.getElementById("uiV4NewTask")?.addEventListener("click", scrollToTasks);
    } else {
      setText(title, "今天要处理什么？");
      setText(description, "从一个常用任务开始。生成结果可以人工复核、保存到项目并继续形成版本记录。");
      actions.innerHTML = `<button id="uiV4NewTask" class="primary" type="button">新建任务</button><button id="uiV4CreateProject" class="secondary" type="button">创建项目</button>`;
      document.getElementById("uiV4NewTask")?.addEventListener("click", scrollToTasks);
      document.getElementById("uiV4CreateProject")?.addEventListener("click", openProjectManager);
    }
  }
  function apply() {
    if (!document.body) return;
    document.body.classList.add("ui-v4-dashboard");
    document.documentElement.dataset.zhilinkDashboard = "v4";
    decorateHomeCards();
    decorateHero();
    renderPending();
    renderUsage();
    window.ZHILINK_UI_V4_DASHBOARD_READY = true;
  }
  function start() {
    apply();
    window.ZHILINK_UI_V4_RUNTIME?.subscribe?.(apply, { immediate: false });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
