/* Connect the approved dashboard redesign to the existing workspace without replacing business logic. */
(() => {
  const CURRENT_PROJECT_STORAGE = "zhilian_current_project_v1";
  const WORKSPACE_KEY_STORAGE = "zhilian_workspace_key_v1";
  const ACCOUNT_READY_EVENT = "zhilink:account-ready";
  const PROJECT_REFRESH_MS = 30000;
  const SVG = {
    menu: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    project: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h7l2 2h9v11H3V6Z"/></svg>',
    knowledge: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h6a3 3 0 0 1 3 3v13a3 3 0 0 0-3-3H5V4ZM19 4h-2a3 3 0 0 0-3 3v13a3 3 0 0 1 3-3h2V4Z"/></svg>',
    report: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h9l4 4v14H6V3Z"/><path d="M15 3v5h5M9 13h6M9 17h4"/></svg>',
    down: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg>',
  };

  let lastProjectSignature = "";
  let latestProjects = { items: [], total: 0 };
  let mutationQueued = false;
  let projectTimer = null;

  function safe(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function readJson(raw, fallback) {
    try { return raw ? JSON.parse(raw) : fallback; } catch (_) { return fallback; }
  }

  function notify(message) {
    if (typeof toast === "function") toast(message);
    else console.info(message);
  }

  function setText(element, value) {
    if (element && element.textContent !== String(value)) element.textContent = String(value);
  }

  function injectStyles() {
    if (document.querySelector("link[data-ui-redesign-live]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "/assets/ui-redesign-live.css";
    link.dataset.uiRedesignLive = "true";
    document.head.appendChild(link);
  }

  function triggerExisting(id) {
    const target = document.getElementById(id);
    if (!target) {
      notify("该功能仍在初始化，请稍后重试。");
      return false;
    }
    target.click();
    return true;
  }

  function accountLabel() {
    const source = document.getElementById("openAccountManager");
    const text = source?.textContent?.trim() || "登录 / 组织";
    if (text === "登录 / 组织") return text;
    const first = text.split(" · ")[0]?.trim();
    return first || "企业账户";
  }

  function buildTopNavigation() {
    const topbar = document.querySelector(".topbar");
    const topActions = document.querySelector(".top-actions");
    if (!topbar || !topActions) return;

    if (!document.getElementById("liveMobileMenu")) {
      const mobile = document.createElement("button");
      mobile.id = "liveMobileMenu";
      mobile.className = "live-mobile-menu";
      mobile.type = "button";
      mobile.setAttribute("aria-label", "打开导航");
      mobile.innerHTML = SVG.menu;
      mobile.addEventListener("click", () => setSidebarOpen(true));
      topbar.insertBefore(mobile, topbar.firstChild);
    }

    if (!document.getElementById("liveTopNav")) {
      const nav = document.createElement("nav");
      nav.id = "liveTopNav";
      nav.className = "live-top-nav";
      nav.setAttribute("aria-label", "工作台快捷入口");
      nav.innerHTML = `
        <button id="liveProjectNav" type="button">${SVG.project}<span>项目</span></button>
        <button id="liveKnowledgeNav" type="button">${SVG.knowledge}<span>知识库</span></button>
        <button id="liveReportNav" type="button">${SVG.report}<span>报告</span></button>
        <div class="live-account-wrap">
          <button id="liveAccountToggle" class="live-account-toggle" type="button" aria-expanded="false">
            <span class="live-account-avatar">企</span><span id="liveAccountLabel">企业账户</span>${SVG.down}
          </button>
          <div id="liveAccountMenu" class="live-account-menu" hidden>
            <button type="button" data-live-account="account">账号、组织与权限</button>
            <button type="button" data-live-account="identity">企业身份设置</button>
            <button type="button" data-live-account="api">模型与 API 配置</button>
            <hr />
            <button type="button" class="live-danger" data-live-account="clear">清空当前会话</button>
          </div>
        </div>`;
      topActions.appendChild(nav);

      document.getElementById("liveProjectNav").addEventListener("click", () => triggerExisting("openProjectManager"));
      document.getElementById("liveKnowledgeNav").addEventListener("click", () => {
        const source = document.getElementById("openKnowledgeBase");
        if (!source || source.hidden) {
          notify("请先登录并选择组织空间后使用知识库。");
          triggerExisting("openAccountManager");
          return;
        }
        source.click();
      });
      document.getElementById("liveReportNav").addEventListener("click", () => {
        if (typeof go === "function") go("report");
      });
      document.getElementById("liveAccountToggle").addEventListener("click", event => {
        event.stopPropagation();
        const menu = document.getElementById("liveAccountMenu");
        const next = menu.hidden;
        menu.hidden = !next;
        document.getElementById("liveAccountToggle").setAttribute("aria-expanded", String(next));
      });
      document.getElementById("liveAccountMenu").addEventListener("click", event => {
        const button = event.target.closest("[data-live-account]");
        if (!button) return;
        closeAccountMenu();
        const action = button.dataset.liveAccount;
        if (action === "account") triggerExisting("openAccountManager");
        if (action === "identity") triggerExisting("openIdentity");
        if (action === "api") openApiModal();
        if (action === "clear") triggerExisting("clearAll");
      });
    }

    syncTopNavigation();
  }

  function closeAccountMenu() {
    const menu = document.getElementById("liveAccountMenu");
    const toggle = document.getElementById("liveAccountToggle");
    if (menu) menu.hidden = true;
    if (toggle) toggle.setAttribute("aria-expanded", "false");
  }

  function syncTopNavigation() {
    setText(document.getElementById("liveAccountLabel"), accountLabel());
    const source = document.getElementById("openKnowledgeBase");
    const button = document.getElementById("liveKnowledgeNav");
    if (button) {
      const available = Boolean(source && !source.hidden);
      button.hidden = !available;
      button.title = available ? source.title || "打开组织知识库" : "登录并选择组织后使用知识库";
    }
  }

  function buildApiModal() {
    const apiPanel = document.getElementById("apiPanel");
    if (!apiPanel) return;
    if (!document.getElementById("liveApiBackdrop")) {
      const backdrop = document.createElement("div");
      backdrop.id = "liveApiBackdrop";
      backdrop.className = "live-api-backdrop";
      backdrop.addEventListener("click", closeApiModal);
      document.body.appendChild(backdrop);
    }
    const panelActions = apiPanel.querySelector(".panel-actions");
    if (panelActions && !document.getElementById("liveApiClose")) {
      const close = document.createElement("button");
      close.id = "liveApiClose";
      close.className = "live-api-close";
      close.type = "button";
      close.setAttribute("aria-label", "关闭模型配置");
      close.textContent = "×";
      close.addEventListener("click", closeApiModal);
      panelActions.appendChild(close);
    }
    const collapse = document.getElementById("toggleApiPanel");
    if (collapse) collapse.hidden = true;
  }

  function openApiModal() {
    buildApiModal();
    const apiPanel = document.getElementById("apiPanel");
    if (!apiPanel) return;
    apiPanel.classList.remove("collapsed");
    document.body.classList.add("live-api-open");
    const original = document.getElementById("openApiSettings");
    if (original) original.click();
    setTimeout(() => document.getElementById("apiKey")?.focus(), 40);
  }

  function closeApiModal() {
    document.body.classList.remove("live-api-open");
  }

  function buildSidebar() {
    const sidebar = document.querySelector(".sidebar");
    if (!sidebar) return;
    const policy = sidebar.querySelector('.nav button[data-section="policy"]');
    if (policy) {
      const textNode = Array.from(policy.childNodes).find(node => node.nodeType === Node.TEXT_NODE);
      if (textNode && textNode.textContent !== "政策助手") textNode.textContent = "政策助手";
    }

    if (!document.getElementById("liveSidebarRecent")) {
      const recent = document.createElement("section");
      recent.id = "liveSidebarRecent";
      recent.className = "live-sidebar-recent";
      recent.innerHTML = `
        <div class="live-sidebar-recent-head"><strong>最近项目</strong><span id="liveSidebarProjectCount">0</span></div>
        <div id="liveSidebarProjectList"><p class="live-sidebar-empty">正在读取项目…</p></div>
        <button class="live-sidebar-all" type="button" id="liveSidebarAllProjects">查看全部项目 →</button>`;
      const oldStatus = sidebar.querySelector(".tool-status-card");
      sidebar.insertBefore(recent, oldStatus || sidebar.lastChild);
      document.getElementById("liveSidebarAllProjects").addEventListener("click", () => {
        setSidebarOpen(false);
        triggerExisting("openProjectManager");
      });
    }

    if (!document.getElementById("liveSidebarFooter")) {
      const footer = document.createElement("div");
      footer.id = "liveSidebarFooter";
      footer.className = "live-sidebar-footer";
      footer.innerHTML = '<button type="button" id="liveHelpButton">帮助与反馈</button>';
      sidebar.appendChild(footer);
      document.getElementById("liveHelpButton").addEventListener("click", () => notify("可通过项目、知识库与人工复核记录反馈具体问题。"));
    }

    if (!document.getElementById("liveMobileBackdrop")) {
      const backdrop = document.createElement("div");
      backdrop.id = "liveMobileBackdrop";
      backdrop.className = "live-mobile-backdrop";
      backdrop.addEventListener("click", () => setSidebarOpen(false));
      document.body.appendChild(backdrop);
    }
  }

  function setSidebarOpen(open) {
    document.body.classList.toggle("live-sidebar-open", Boolean(open));
    document.querySelector(".sidebar")?.classList.toggle("live-open", Boolean(open));
  }

  function decorateHero() {
    const hero = document.querySelector("#home .hero-card");
    if (!hero) return;
    const visual = hero.querySelector(".hero-visual");
    if (visual && !visual.querySelector(".live-ai-orbit")) {
      const orbit = document.createElement("div");
      orbit.className = "live-ai-orbit";
      orbit.textContent = "AI";
      visual.appendChild(orbit);
    }

    const actions = hero.querySelector(".hero-content .button-row");
    if (actions && !actions.dataset.liveRedesign) {
      actions.dataset.liveRedesign = "true";
      actions.innerHTML = `
        <button id="liveNewTask" class="primary" type="button">＋ 新建处理任务&nbsp; →</button>
        <button id="liveContinueProject" class="secondary" type="button">继续最近项目</button>`;
      document.getElementById("liveNewTask").addEventListener("click", () => {
        const grid = document.querySelector("#home .module-grid");
        if (!grid) return;
        grid.scrollIntoView({ behavior: "smooth", block: "center" });
        grid.classList.remove("live-task-pulse");
        requestAnimationFrame(() => grid.classList.add("live-task-pulse"));
        setTimeout(() => grid.querySelector(".module-card")?.focus(), 380);
      });
      document.getElementById("liveContinueProject").addEventListener("click", () => triggerExisting("openProjectManager"));
    }

    const status = document.querySelector("#home .readiness-row:first-of-type");
    if (status && !status.dataset.liveApiTrigger) {
      status.dataset.liveApiTrigger = "true";
      status.setAttribute("role", "button");
      status.tabIndex = 0;
      status.title = "打开模型与 API 配置";
      status.addEventListener("click", openApiModal);
      status.addEventListener("keydown", event => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openApiModal();
        }
      });
    }

    const toolbar = document.querySelector("#home .section-toolbar");
    if (toolbar) {
      setText(toolbar.querySelector("h3"), "常用任务");
      setText(toolbar.querySelector("p"), "选择一个任务，开始整理企业运营材料。");
    }
  }

  function decorateTaskCards() {
    document.querySelectorAll("#home .module-card").forEach(card => {
      const key = card.dataset.toolKey || "";
      if (!card.dataset.liveInteractive) {
        card.dataset.liveInteractive = "true";
        card.tabIndex = 0;
        card.setAttribute("role", "button");
        card.addEventListener("keydown", event => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            card.click();
          }
        });
      }
      const footerLabel = card.querySelector(".module-footer span");
      const labels = { profile: "完善档案", report: "查看报告" };
      setText(footerLabel, labels[key] || "开始处理");
    });
  }

  function buildHomePanels() {
    const home = document.getElementById("home");
    const recent = home?.querySelector(".recent-card");
    const governance = home?.querySelector(".governance-card");
    if (!home || !recent || !governance) return;

    let grid = document.getElementById("liveHomeGrid");
    if (!grid) {
      grid = document.createElement("div");
      grid.id = "liveHomeGrid";
      grid.className = "live-home-grid";
      governance.parentNode.insertBefore(grid, governance);
      grid.appendChild(recent);

      const pending = document.createElement("section");
      pending.id = "livePendingPanel";
      pending.className = "live-home-panel";
      pending.innerHTML = `
        <div class="live-panel-head"><h3>待确认事项</h3><span id="livePendingCount">0 项</span></div>
        <div id="livePendingList" class="live-pending-list"></div>`;
      grid.appendChild(pending);

      const usage = document.createElement("section");
      usage.id = "liveUsagePanel";
      usage.className = "live-home-panel live-usage-panel";
      usage.innerHTML = `
        <div class="live-panel-head"><h3>工作台数据</h3><span>实时数据</span></div>
        <div id="liveMetrics" class="live-metrics"></div>
        <p id="liveUsageNote" class="live-usage-note"></p>`;
      grid.appendChild(usage);
    }
  }

  function currentProject() {
    return readJson(localStorage.getItem(CURRENT_PROJECT_STORAGE), null);
  }

  function collectPendingItems() {
    const items = [];
    const seen = new Set();
    const pattern = /(待确认|需确认|人工确认|尚未明确|未明确|待补充|待核实|需核实)/;
    const keys = typeof resultKeys !== "undefined" ? resultKeys : ["profile", "meeting", "contract", "policy", "match", "landing"];
    const titles = typeof resultTitles !== "undefined" ? resultTitles : {};
    const results = typeof state !== "undefined" ? state.results || {} : readJson(sessionStorage.getItem("zhilian_results"), {});

    keys.forEach(key => {
      const content = String(results[key] || "");
      if (!content) return;
      content.split(/\n+/).forEach(raw => {
        const text = raw
          .replace(/^[#>*\-\d.、\s]+/, "")
          .replace(/\[[A-Z0-9-]+\]/g, "")
          .replace(/\s+/g, " ")
          .trim();
        if (!text || !pattern.test(text) || seen.has(text)) return;
        seen.add(text);
        items.push({ title: text.slice(0, 70), source: titles[key] || key });
      });
    });

    document.querySelectorAll(".review-workflow-bar strong").forEach(node => {
      const text = node.textContent.trim();
      if (!/(待审核|退回|失效|尚未建立)/.test(text)) return;
      const panel = node.closest(".result-panel");
      const id = panel?.id?.replace(/Result$/, "") || "";
      const title = `${titles[id] || "材料"}：${text}`;
      if (seen.has(title)) return;
      seen.add(title);
      items.push({ title, source: "人工复核" });
    });

    return items.slice(0, 4);
  }

  function renderPending() {
    const list = document.getElementById("livePendingList");
    const count = document.getElementById("livePendingCount");
    if (!list || !count) return;
    const items = collectPendingItems();
    setText(count, `${items.length} 项`);
    const html = items.length
      ? items.map(item => `<article class="live-pending-item"><span class="live-pending-icon">!</span><div><strong>${safe(item.title)}</strong><small>${safe(item.source)} · 请人工核对后使用</small></div></article>`).join("")
      : '<p class="live-panel-empty">当前生成结果中没有识别到待确认事项。新材料生成后会自动更新。</p>';
    if (list.innerHTML !== html) list.innerHTML = html;
  }

  function reviewCounts() {
    let confirmed = 0;
    let pending = 0;
    document.querySelectorAll(".review-workflow-bar strong").forEach(node => {
      const text = node.textContent;
      if (/(批准|已确认)/.test(text)) confirmed += 1;
      if (/(待审核|退回|失效|尚未建立)/.test(text)) pending += 1;
    });
    return { confirmed, pending };
  }

  function renderUsage() {
    const metrics = document.getElementById("liveMetrics");
    const note = document.getElementById("liveUsageNote");
    if (!metrics || !note) return;
    const results = typeof state !== "undefined" ? state.results || {} : readJson(sessionStorage.getItem("zhilian_results"), {});
    const generated = Object.entries(results).filter(([key, value]) => key !== "report" && String(value || "").trim()).length;
    const project = currentProject();
    const reviews = reviewCounts();
    const html = `
      <div class="live-metric"><strong>${generated}</strong><span>已生成材料</span></div>
      <div class="live-metric"><strong>${latestProjects.total || 0}</strong><span>可访问项目</span></div>
      <div class="live-metric"><strong>${reviews.confirmed}</strong><span>已确认 / 批准</span></div>
      <div class="live-metric"><strong>${reviews.pending}</strong><span>待复核状态</span></div>`;
    if (metrics.innerHTML !== html) metrics.innerHTML = html;
    setText(note, project ? `当前项目：${project.name} · v${project.lock_version}${project.status === "archived" ? " · 已归档" : ""}` : "当前未打开持久化项目。可从顶部“项目”创建或载入项目。" );
  }

  function projectHeaders() {
    const organization = window.ZHILINK_ACCOUNT?.getActiveOrganization?.() || null;
    if (organization) return {};
    const key = localStorage.getItem(WORKSPACE_KEY_STORAGE) || "";
    return key ? { "X-Workspace-Key": key } : {};
  }

  async function fetchProjects() {
    try {
      const response = await fetch("/api/projects?limit=4&offset=0", {
        headers: projectHeaders(),
        credentials: "same-origin",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      latestProjects = { items: Array.isArray(data.items) ? data.items : [], total: Number(data.total || 0) };
      renderSidebarProjects();
      renderUsage();
    } catch (_) {
      latestProjects = { items: [], total: 0 };
      renderSidebarProjects(true);
      renderUsage();
    }
  }

  function projectTime(value) {
    if (!value) return "";
    try { return new Date(value).toLocaleString([], { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }); }
    catch (_) { return ""; }
  }

  function renderSidebarProjects(failed = false) {
    const list = document.getElementById("liveSidebarProjectList");
    const count = document.getElementById("liveSidebarProjectCount");
    if (!list || !count) return;
    setText(count, latestProjects.total || 0);
    const signature = JSON.stringify({ failed, total: latestProjects.total, items: latestProjects.items.map(item => [item.id, item.name, item.lock_version, item.updated_at]) });
    if (signature === lastProjectSignature) return;
    lastProjectSignature = signature;
    if (failed) {
      list.innerHTML = '<p class="live-sidebar-empty">项目列表暂时不可用，可点击“查看全部项目”重试。</p>';
      return;
    }
    if (!latestProjects.items.length) {
      list.innerHTML = '<p class="live-sidebar-empty">暂无已保存项目。创建项目后会显示在这里。</p>';
      return;
    }
    list.innerHTML = latestProjects.items.slice(0, 3).map(item => `
      <button class="live-sidebar-project" type="button" data-live-project-id="${safe(item.id)}">
        <strong>${safe(item.name)}</strong><small>v${safe(item.lock_version)} · ${safe(projectTime(item.updated_at))}</small>
      </button>`).join("");
    list.querySelectorAll("[data-live-project-id]").forEach(button => {
      button.addEventListener("click", () => openProjectFromSidebar(button.dataset.liveProjectId));
    });
  }

  function openProjectFromSidebar(projectId) {
    setSidebarOpen(false);
    if (!triggerExisting("openProjectManager")) return;
    let attempts = 0;
    const timer = window.setInterval(() => {
      attempts += 1;
      const selector = `[data-load-project="${CSS.escape(projectId)}"]`;
      const button = document.querySelector(selector);
      if (button) {
        window.clearInterval(timer);
        button.click();
      } else if (attempts > 12) {
        window.clearInterval(timer);
      }
    }, 180);
  }

  function refreshDashboard() {
    buildTopNavigation();
    buildApiModal();
    buildSidebar();
    decorateHero();
    decorateTaskCards();
    buildHomePanels();
    syncTopNavigation();
    renderPending();
    renderUsage();
  }

  function queueRefresh() {
    if (mutationQueued) return;
    mutationQueued = true;
    window.setTimeout(() => {
      mutationQueued = false;
      refreshDashboard();
    }, 40);
  }

  function wrapExistingFunctions() {
    if (typeof updateProgress === "function" && !updateProgress.__liveRedesignWrapped) {
      const originalUpdateProgress = updateProgress;
      const wrappedUpdateProgress = function liveRedesignUpdateProgress(...args) {
        const value = originalUpdateProgress(...args);
        queueRefresh();
        return value;
      };
      wrappedUpdateProgress.__liveRedesignWrapped = true;
      updateProgress = wrappedUpdateProgress;
    }

    if (typeof go === "function" && !go.__liveRedesignWrapped) {
      const originalGo = go;
      const wrappedGo = function liveRedesignGo(section) {
        const value = originalGo(section);
        setSidebarOpen(false);
        closeAccountMenu();
        queueRefresh();
        return value;
      };
      wrappedGo.__liveRedesignWrapped = true;
      go = wrappedGo;
    }
  }

  function bindGlobalEvents() {
    document.addEventListener("click", event => {
      const menu = document.getElementById("liveAccountMenu");
      const wrap = document.querySelector(".live-account-wrap");
      if (menu && wrap && !menu.hidden && !wrap.contains(event.target)) closeAccountMenu();
      if (event.target.closest(".nav button")) setSidebarOpen(false);
    });
    document.addEventListener("keydown", event => {
      if (event.key !== "Escape") return;
      closeAccountMenu();
      closeApiModal();
      setSidebarOpen(false);
    });
    window.addEventListener("storage", event => {
      if ([CURRENT_PROJECT_STORAGE, WORKSPACE_KEY_STORAGE].includes(event.key)) {
        fetchProjects();
        queueRefresh();
      }
    });
    window.addEventListener(ACCOUNT_READY_EVENT, () => {
      fetchProjects();
      queueRefresh();
    });
    document.addEventListener(ACCOUNT_READY_EVENT, () => {
      fetchProjects();
      queueRefresh();
    });
  }

  function init() {
    injectStyles();
    document.body.classList.add("ui-redesign-live");
    wrapExistingFunctions();
    bindGlobalEvents();
    refreshDashboard();
    fetchProjects();

    const observer = new MutationObserver(queueRefresh);
    observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["class", "hidden"] });
    projectTimer = window.setInterval(fetchProjects, PROJECT_REFRESH_MS);
    window.addEventListener("beforeunload", () => {
      observer.disconnect();
      if (projectTimer) window.clearInterval(projectTimer);
    }, { once: true });
  }

  window.ZHILINK_UI_REDESIGN_LIVE_READY = true;
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
  else window.setTimeout(init, 0);
})();
