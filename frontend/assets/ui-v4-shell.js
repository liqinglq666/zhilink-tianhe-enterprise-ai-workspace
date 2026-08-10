/* UI V4 shell: owns workspace chrome and lightweight dashboard context without legacy visual layers. */
(() => {
  const VERSION = "20260810.3";
  const CURRENT_PROJECT_STORAGE = "zhilian_current_project_v1";
  const WORKSPACE_KEY_STORAGE = "zhilian_workspace_key_v1";
  const ACCOUNT_READY_EVENT = "zhilink:account-ready";
  const PROJECT_REFRESH_MS = 30000;
  const MODULES = {
    home: { label: "工作首页", icon: "home" },
    profile: { label: "企业档案", result: "企业档案 · 生成结果", icon: "profile" },
    meeting: { label: "会议纪要", result: "会议纪要 · AI 生成结果", icon: "meeting" },
    contract: { label: "合同审阅", result: "合同风险 · AI 审阅结果", icon: "contract" },
    policy: { label: "政策助手", result: "政策方向 · AI 建议结果", icon: "policy" },
    match: { label: "供需协作", result: "供需协作 · AI 方案结果", icon: "match" },
    landing: { label: "实施计划", result: "实施计划 · AI 生成结果", icon: "plan" },
    report: { label: "报告归档", result: "运营报告 · 汇总与导出", icon: "report" },
  };
  const ICONS = {
    menu: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    down: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg>',
    home: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10.5V20h13v-9.5M9 20v-6h6v6"/></svg>',
    meeting: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3.5h9l3 3V21H6z"/><path d="M15 3.5V7h3M9 12h6M9 16h4"/><path d="M4 9.5a3 3 0 0 1 6 0v1a3 3 0 0 1-6 0z"/><path d="M7 13.5v2M5 15.5h4"/></svg>',
    contract: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3.5h9l3 3V21H6z"/><path d="M15 3.5V7h3M9 11h5M9 15h3"/><circle cx="15.5" cy="15.5" r="4"/><path d="m18.5 18.5 2 2M14.2 15.5l1 1 1.8-2"/></svg>',
    policy: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9h16M6 9V7l6-3 6 3v2M7 9v8M11 9v8M15 9v8M19 17H5v3h14z"/></svg>',
    match: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8.5 12.5 11 15a2.4 2.4 0 0 0 3.4 0l4.1-4.1"/><path d="m9.5 8.5 2-2a2.8 2.8 0 0 1 4 0l4 4-3 3"/><path d="m14.5 8.5-2-2a2.8 2.8 0 0 0-4 0l-4 4 4 4"/></svg>',
    profile: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20V8h8v12M12 20V4h8v16"/><path d="M7 11h2M7 14h2M15 7h2M15 10h2M15 13h2"/><circle cx="8" cy="5" r="2.5"/></svg>',
    plan: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M7 3v4M17 3v4M3.5 9h17"/><path d="m7 14 2 2 4-4 4 4"/></svg>',
    report: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3.5h9l3 3V21H6z"/><path d="M15 3.5V7h3M9 17v-3M12 17v-6M15 17v-4"/></svg>',
    account: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="3.5"/><path d="M5 20a7 7 0 0 1 14 0"/></svg>',
    arrow: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M14 7l5 5-5 5"/></svg>',
  };

  let latestProjects = { items: [], total: 0 };
  let lastProjectSignature = "";
  let observer = null;
  let projectTimer = null;
  let queued = false;

  function byId(id) { return document.getElementById(id); }
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
  function setText(element, value) {
    if (element && element.textContent !== String(value)) element.textContent = String(value);
  }
  function notify(message) {
    if (typeof toast === "function") toast(message);
    else console.info(message);
  }

  function ensureStyles() {
    if (document.querySelector("link[data-ui-v4-shell]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `/assets/ui-v4-shell.css?v=${VERSION}`;
    link.dataset.uiV4Shell = "true";
    document.head.appendChild(link);
  }

  function ensureWorkspaceKey() {
    let key = localStorage.getItem(WORKSPACE_KEY_STORAGE) || "";
    if (key.length >= 32) return key;
    if (!window.crypto?.getRandomValues) return "";
    const bytes = new Uint8Array(32);
    window.crypto.getRandomValues(bytes);
    key = Array.from(bytes, value => value.toString(16).padStart(2, "0")).join("");
    localStorage.setItem(WORKSPACE_KEY_STORAGE, key);
    return key;
  }

  function triggerExisting(id) {
    const target = byId(id);
    if (!target) {
      notify("该功能仍在初始化，请稍后重试。");
      return false;
    }
    target.click();
    return true;
  }

  function accountLabel() {
    const source = byId("openAccountManager");
    const text = source?.textContent?.trim() || "登录 / 组织";
    if (text === "登录 / 组织") return text;
    return text.split(" · ")[0]?.trim() || "企业账户";
  }

  function setSidebarOpen(open) {
    document.body.classList.toggle("ui-v4-sidebar-open", Boolean(open));
    document.querySelector(".sidebar")?.classList.toggle("ui-v4-open", Boolean(open));
    const trigger = byId("uiV4MobileMenu");
    if (trigger) trigger.setAttribute("aria-expanded", String(Boolean(open)));
  }

  function closeAccountMenu() {
    const menu = byId("uiV4AccountMenu");
    const toggle = byId("uiV4AccountToggle");
    if (menu) menu.hidden = true;
    if (toggle) toggle.setAttribute("aria-expanded", "false");
  }

  function openModelConfig() {
    const panel = byId("apiPanel");
    if (!panel) return false;
    panel.classList.remove("collapsed");
    document.body.classList.add("ui-v4-api-open");
    const trigger = byId("openApiSettings");
    if (trigger) trigger.click();
    return true;
  }

  function buildTopNavigation() {
    const topbar = document.querySelector(".topbar");
    const topActions = document.querySelector(".top-actions");
    if (!topbar || !topActions) return;

    if (!byId("uiV4MobileMenu")) {
      const mobile = document.createElement("button");
      mobile.id = "uiV4MobileMenu";
      mobile.className = "ui-v4-mobile-menu";
      mobile.type = "button";
      mobile.setAttribute("aria-label", "打开导航");
      mobile.setAttribute("aria-controls", "navList");
      mobile.setAttribute("aria-expanded", "false");
      mobile.innerHTML = ICONS.menu;
      mobile.addEventListener("click", () => setSidebarOpen(true));
      topbar.insertBefore(mobile, topbar.firstChild);
    }

    if (!byId("uiV4TopNav")) {
      const nav = document.createElement("nav");
      nav.id = "uiV4TopNav";
      nav.className = "ui-v4-top-nav";
      nav.setAttribute("aria-label", "项目与账户");
      nav.innerHTML = `
        <div class="ui-v4-account-wrap">
          <button id="uiV4AccountToggle" class="ui-v4-account-toggle" type="button" aria-expanded="false" aria-controls="uiV4AccountMenu">
            <span class="ui-v4-account-avatar">${ICONS.account}</span><span id="uiV4AccountLabel">企业账户</span>${ICONS.down}
          </button>
          <div id="uiV4AccountMenu" class="ui-v4-account-menu" hidden>
            <button type="button" data-ui-v4-account="account">账户与组织</button>
            <button type="button" data-ui-v4-account="identity">使用身份</button>
            <button type="button" data-ui-v4-account="api">模型配置</button>
            <hr />
            <button type="button" class="ui-v4-danger" data-ui-v4-account="clear">清空本次会话</button>
          </div>
        </div>`;
      topActions.appendChild(nav);

      byId("uiV4AccountToggle")?.addEventListener("click", event => {
        event.stopPropagation();
        const menu = byId("uiV4AccountMenu");
        if (!menu) return;
        const opening = menu.hidden;
        menu.hidden = !opening;
        byId("uiV4AccountToggle")?.setAttribute("aria-expanded", String(opening));
      });
      byId("uiV4AccountMenu")?.addEventListener("click", event => {
        const button = event.target.closest?.("[data-ui-v4-account]");
        if (!button) return;
        closeAccountMenu();
        const action = button.dataset.uiV4Account;
        if (action === "account") triggerExisting("openAccountManager");
        else if (action === "identity") triggerExisting("openIdentity");
        else if (action === "api") openModelConfig();
        else if (action === "clear") triggerExisting("clearAll");
      });
    }

    setText(byId("uiV4AccountLabel"), accountLabel());
  }

  function buildSidebar() {
    const sidebar = document.querySelector(".sidebar");
    if (!sidebar) return;

    if (!byId("uiV4SidebarRecent")) {
      const recent = document.createElement("section");
      recent.id = "uiV4SidebarRecent";
      recent.className = "ui-v4-sidebar-recent";
      recent.innerHTML = `
        <div class="ui-v4-sidebar-recent-head"><strong>最近项目</strong><span id="uiV4SidebarProjectCount">0</span></div>
        <div id="uiV4SidebarProjectList"><p class="ui-v4-sidebar-empty">正在读取项目…</p></div>
        <button class="ui-v4-sidebar-all" type="button" id="uiV4SidebarAllProjects">查看全部项目 →</button>`;
      const oldStatus = sidebar.querySelector(".tool-status-card");
      sidebar.insertBefore(recent, oldStatus || sidebar.lastChild);
      byId("uiV4SidebarAllProjects")?.addEventListener("click", () => {
        setSidebarOpen(false);
        triggerExisting("openProjectManager");
      });
    }

    if (!byId("uiV4MobileBackdrop")) {
      const backdrop = document.createElement("div");
      backdrop.id = "uiV4MobileBackdrop";
      backdrop.className = "ui-v4-mobile-backdrop";
      backdrop.addEventListener("click", () => setSidebarOpen(false));
      document.body.appendChild(backdrop);
    }
  }

  function decorateNavigationIcons() {
    document.querySelectorAll("#navList button[data-section]").forEach(button => {
      const config = MODULES[button.dataset.section];
      const holder = button.querySelector(":scope > span");
      if (!config || !holder || holder.dataset.uiV4Icon === "true") return;
      holder.className = "ui-v4-nav-icon";
      holder.innerHTML = ICONS[config.icon] || ICONS.home;
      holder.dataset.uiV4Icon = "true";
    });
  }

  function decorateBusinessPages() {
    Object.entries(MODULES).forEach(([id, config]) => {
      if (id === "home") return;
      const page = byId(id);
      const content = page?.querySelector(":scope > .content-card") || page?.querySelector(".content-card");
      const result = page?.querySelector(":scope > .result-panel") || page?.querySelector(".result-panel");
      if (!page || !content || !result) return;

      page.classList.add("ui-v4-business-page");
      page.dataset.uiV4Module = id;
      const head = content.querySelector(".section-head");
      const iconHolder = head?.querySelector(":scope > span");
      if (iconHolder && iconHolder.dataset.uiV4Icon !== "true") {
        iconHolder.innerHTML = ICONS[config.icon] || ICONS.home;
        iconHolder.dataset.uiV4Icon = "true";
        iconHolder.setAttribute("aria-hidden", "true");
      }

      if (head && !content.querySelector(".ui-v4-module-meta")) {
        const meta = document.createElement("div");
        meta.className = "ui-v4-module-meta";
        const labels = id === "report"
          ? ["汇总已有结果", "支持多格式导出", "不导出 API Key"]
          : id === "profile"
            ? ["可选上下文", "支持快速示例", "结果可归档"]
            : ["AI 辅助生成", "人工复核后使用", "结果可归档"];
        meta.innerHTML = labels.map(label => `<span>${label}</span>`).join("");
        head.insertAdjacentElement("afterend", meta);
      }

      result.setAttribute("aria-label", config.result);
      content.querySelectorAll("textarea").forEach(textarea => textarea.setAttribute("spellcheck", "false"));
      content.querySelectorAll(".sticky-actions button.primary").forEach(button => {
        if (button.dataset.uiV4Arrow === "true") return;
        button.insertAdjacentHTML("beforeend", ICONS.arrow);
        button.dataset.uiV4Arrow = "true";
      });
    });
  }

  function decorateHomeCards() {
    document.querySelectorAll("#home .module-card[data-tool-key]").forEach(card => {
      const config = MODULES[card.dataset.toolKey];
      const holder = card.querySelector(".module-icon");
      if (config && holder && holder.dataset.uiV4Icon !== "true") {
        holder.classList.add("ui-v4-module-icon");
        holder.innerHTML = ICONS[config.icon] || ICONS.home;
        holder.dataset.uiV4Icon = "true";
      }
      const button = card.querySelector(".module-footer button");
      if (button && button.dataset.uiV4Arrow !== "true") {
        button.insertAdjacentHTML("beforeend", ICONS.arrow);
        button.dataset.uiV4Arrow = "true";
      }
    });
  }

  function buildHomePanels() {
    const home = byId("home");
    const recent = home?.querySelector(".recent-card");
    const governance = home?.querySelector(".governance-card");
    if (!home || !recent || !governance) return;

    let grid = byId("uiV4HomeGrid");
    if (!grid) {
      grid = document.createElement("div");
      grid.id = "uiV4HomeGrid";
      grid.className = "ui-v4-home-grid";
      governance.parentNode.insertBefore(grid, governance);
      grid.appendChild(recent);

      const pending = document.createElement("section");
      pending.id = "uiV4PendingPanel";
      pending.className = "ui-v4-home-panel";
      pending.innerHTML = `
        <div class="ui-v4-panel-head"><h3>待确认事项</h3><span id="uiV4PendingCount">0 项</span></div>
        <div id="uiV4PendingList" class="ui-v4-pending-list"></div>`;
      grid.appendChild(pending);

      const usage = document.createElement("section");
      usage.id = "uiV4UsagePanel";
      usage.className = "ui-v4-home-panel ui-v4-usage-panel";
      usage.innerHTML = `
        <div class="ui-v4-panel-head"><h3>工作台数据</h3><span>实时数据</span></div>
        <div id="uiV4Metrics" class="ui-v4-metrics"></div>
        <p id="uiV4UsageNote" class="ui-v4-usage-note"></p>`;
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
    const list = byId("uiV4PendingList");
    const count = byId("uiV4PendingCount");
    if (!list || !count) return;
    const items = collectPendingItems();
    setText(count, `${items.length} 项`);
    const html = items.length
      ? items.map(item => `<article class="ui-v4-pending-item"><span class="ui-v4-pending-icon">!</span><div><strong>${safe(item.title)}</strong><small>${safe(item.source)} · 请人工核对后使用</small></div></article>`).join("")
      : '<p class="ui-v4-panel-empty">当前生成结果中没有识别到待确认事项。新材料生成后会自动更新。</p>';
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
    const metrics = byId("uiV4Metrics");
    const note = byId("uiV4UsageNote");
    if (!metrics || !note) return;
    const results = typeof state !== "undefined" ? state.results || {} : readJson(sessionStorage.getItem("zhilian_results"), {});
    const generated = Object.entries(results).filter(([key, value]) => key !== "report" && String(value || "").trim()).length;
    const project = currentProject();
    const reviews = reviewCounts();
    const html = `
      <div class="ui-v4-metric"><strong>${generated}</strong><span>已生成材料</span></div>
      <div class="ui-v4-metric"><strong>${latestProjects.total || 0}</strong><span>可访问项目</span></div>
      <div class="ui-v4-metric"><strong>${reviews.confirmed}</strong><span>已确认 / 批准</span></div>
      <div class="ui-v4-metric"><strong>${reviews.pending}</strong><span>待复核状态</span></div>`;
    if (metrics.innerHTML !== html) metrics.innerHTML = html;
    setText(note, project
      ? `当前项目：${project.name} · v${project.lock_version}${project.status === "archived" ? " · 已归档" : ""}`
      : "当前未打开持久化项目。可从顶部当前项目入口创建或载入项目。");
  }

  function projectHeaders() {
    const organization = window.ZHILINK_ACCOUNT?.getActiveOrganization?.() || null;
    if (organization) return {};
    const key = ensureWorkspaceKey();
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
    } catch (_) {
      latestProjects = { items: [], total: 0 };
      renderSidebarProjects(true);
    }
    renderUsage();
  }

  function projectTime(value) {
    if (!value) return "";
    try { return new Date(value).toLocaleString([], { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }); }
    catch (_) { return ""; }
  }

  function renderSidebarProjects(failed = false) {
    const list = byId("uiV4SidebarProjectList");
    const count = byId("uiV4SidebarProjectCount");
    if (!list || !count) return;
    setText(count, latestProjects.total || 0);
    const signature = JSON.stringify({ failed, total: latestProjects.total, items: latestProjects.items.map(item => [item.id, item.name, item.lock_version, item.updated_at]) });
    if (signature === lastProjectSignature) return;
    lastProjectSignature = signature;
    if (failed) {
      list.innerHTML = '<p class="ui-v4-sidebar-empty">项目列表暂时不可用，可点击“查看全部项目”重试。</p>';
      return;
    }
    if (!latestProjects.items.length) {
      list.innerHTML = '<p class="ui-v4-sidebar-empty">暂无已保存项目。创建项目后会显示在这里。</p>';
      return;
    }
    list.innerHTML = latestProjects.items.slice(0, 3).map(item => `
      <button class="ui-v4-sidebar-project" type="button" data-ui-v4-project-id="${safe(item.id)}">
        <strong>${safe(item.name)}</strong><small>v${safe(item.lock_version)} · ${safe(projectTime(item.updated_at))}</small>
      </button>`).join("");
    list.querySelectorAll("[data-ui-v4-project-id]").forEach(button => {
      button.addEventListener("click", () => openProjectFromSidebar(button.dataset.uiV4ProjectId));
    });
  }

  function openProjectFromSidebar(projectId) {
    setSidebarOpen(false);
    if (!triggerExisting("openProjectManager")) return;
    let attempts = 0;
    const timer = window.setInterval(() => {
      attempts += 1;
      const button = document.querySelector(`[data-load-project="${CSS.escape(projectId)}"]`);
      if (button) {
        window.clearInterval(timer);
        button.click();
      } else if (attempts > 12) {
        window.clearInterval(timer);
      }
    }, 180);
  }

  function bindGlobalEvents() {
    document.addEventListener("click", event => {
      const menu = byId("uiV4AccountMenu");
      const wrap = document.querySelector(".ui-v4-account-wrap");
      if (menu && wrap && !menu.hidden && !wrap.contains(event.target)) closeAccountMenu();
      if (event.target.closest?.(".nav button")) setSidebarOpen(false);
    });
    document.addEventListener("keydown", event => {
      if (event.key !== "Escape") return;
      closeAccountMenu();
      setSidebarOpen(false);
    });
    window.addEventListener("storage", event => {
      if ([CURRENT_PROJECT_STORAGE, WORKSPACE_KEY_STORAGE].includes(event.key)) {
        fetchProjects();
        queueApply();
      }
    });
    [window, document].forEach(target => target.addEventListener(ACCOUNT_READY_EVENT, () => {
      fetchProjects();
      queueApply();
    }));
    window.addEventListener("zhilink:workspace-state-change", queueApply);
  }

  function apply() {
    ensureStyles();
    if (!document.body) return;
    document.body.classList.add("ui-v4-shell");
    document.documentElement.dataset.zhilinkUi = "v4";
    buildTopNavigation();
    buildSidebar();
    decorateNavigationIcons();
    decorateBusinessPages();
    decorateHomeCards();
    buildHomePanels();
    setText(byId("uiV4AccountLabel"), accountLabel());
    renderPending();
    renderUsage();
    window.ZHILINK_UI_V4_SHELL_READY = true;
  }

  function queueApply() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      apply();
    });
  }

  function installObserver() {
    if (observer || !document.body) return;
    observer = new MutationObserver(mutations => {
      const relevant = mutations.some(mutation => {
        if (mutation.type === "characterData") return true;
        if (mutation.type === "attributes") return ["class", "hidden"].includes(mutation.attributeName);
        return mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0;
      });
      if (relevant) queueApply();
    });
    observer.observe(document.body, {
      subtree: true,
      childList: true,
      characterData: true,
      attributes: true,
      attributeFilter: ["class", "hidden"],
    });
  }

  function start() {
    ensureWorkspaceKey();
    apply();
    bindGlobalEvents();
    installObserver();
    fetchProjects();
    projectTimer = window.setInterval(fetchProjects, PROJECT_REFRESH_MS);
    window.addEventListener("beforeunload", () => {
      observer?.disconnect();
      if (projectTimer) window.clearInterval(projectTimer);
    }, { once: true });
  }

  window.ZHILINK_UI_V4_SHELL = {
    openModelConfig,
    closeAccountMenu,
    setSidebarOpen,
    refresh: queueApply,
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
