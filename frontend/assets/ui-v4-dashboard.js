/* UI V4 dashboard: task-first home workspace, backed only by UI V4 shell primitives. */
(() => {
  const VERSION = "20260811.1";
  const contracts = window.ZHILINK_WORKSPACE_CONTRACTS;
  if (!contracts) throw new Error("Workspace contracts must load before dashboard.");

  const CURRENT_PROJECT_STORAGE = contracts.storage.currentProject;
  const RESULTS_STORAGE = contracts.storage.results;
  const META_STORAGE = contracts.storage.meta;
  const MODULE_ORDER = ["meeting", "contract", "policy", "match", "profile", "landing"];

  function readJson(raw, fallback) { try { return raw ? JSON.parse(raw) : fallback; } catch (_) { return fallback; } }
  function setText(element, value) { if (element && element.textContent !== String(value)) element.textContent = String(value); }
  function ensureStyles() {
    if (document.querySelector("link[data-ui-v4-dashboard]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `/assets/ui-v4-dashboard.css?v=${VERSION}`;
    link.dataset.uiV4Dashboard = "true";
    document.head.appendChild(link);
  }
  function currentProject() { return readJson(localStorage.getItem(CURRENT_PROJECT_STORAGE), null); }
  function projectSignature(project) {
    if (!project) return "none";
    return [project.id || "", project.name || "", project.status || "", project.lock_version || "", project.updated_at || ""].join("|");
  }
  function latestWorkSection() {
    const meta = typeof state !== "undefined" ? state.meta || {} : readJson(sessionStorage.getItem(META_STORAGE), {});
    const results = typeof state !== "undefined" ? state.results || {} : readJson(sessionStorage.getItem(RESULTS_STORAGE), {});
    const candidates = MODULE_ORDER.filter(key => String(results[key] || "").trim()).map(key => ({ key, time: Date.parse(meta[key]?.time || "") || 0 }));
    candidates.sort((a, b) => b.time - a.time);
    return candidates[0]?.key || "meeting";
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
    hero.classList.add("ui-v4-work-hero");
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
  function arrangeAttentionPanel() {
    const overview = document.querySelector("#home .overview-panel");
    const pending = document.getElementById("uiV4PendingPanel");
    if (!overview || !pending) return;
    pending.classList.add("ui-v4-attention-panel");
    if (pending.parentElement !== overview) overview.appendChild(pending);
    setText(pending.querySelector(".ui-v4-panel-head h3"), "需要你处理");
  }
  function decorateTaskSection() {
    const toolbar = document.querySelector("#home > .section-toolbar");
    if (toolbar) {
      setText(toolbar.querySelector("h3"), "新建任务");
      setText(toolbar.querySelector("p"), "选择会议、合同、政策或供需事项开始处理；企业档案与实施计划作为辅助能力。 ");
    }
    document.querySelectorAll("#home .module-card").forEach(card => {
      const key = card.dataset.toolKey || "";
      card.classList.toggle("ui-v4-secondary-task", ["profile", "landing"].includes(key));
    });
  }
  function decorateLowerPanels() {
    const grid = document.getElementById("uiV4HomeGrid");
    const recent = document.querySelector("#home .recent-card");
    const usage = document.getElementById("uiV4UsagePanel");
    if (!grid || !recent || !usage) return;
    grid.classList.add("ui-v4-secondary-grid");
    recent.classList.add("ui-v4-recent-panel");
    usage.classList.add("ui-v4-usage-panel");
    setText(recent.querySelector(".section-toolbar h3"), "最近材料");
    setText(usage.querySelector(".ui-v4-panel-head h3"), "工作状态");
  }
  function simplifyGovernance() {
    const governance = document.querySelector("#home .governance-card");
    if (!governance) return;
    governance.classList.add("ui-v4-safety-strip");
    governance.setAttribute("aria-label", "使用边界");
  }
  function apply() {
    ensureStyles();
    if (!document.body) return;
    document.body.classList.add("ui-v4-dashboard");
    document.documentElement.dataset.zhilinkDashboard = "v4";
    decorateHero();
    arrangeAttentionPanel();
    decorateTaskSection();
    decorateLowerPanels();
    simplifyGovernance();
    window.ZHILINK_UI_V4_DASHBOARD_READY = true;
  }
  function start() {
    apply();
    window.ZHILINK_UI_V4_RUNTIME?.subscribe?.(apply, { immediate: false });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
