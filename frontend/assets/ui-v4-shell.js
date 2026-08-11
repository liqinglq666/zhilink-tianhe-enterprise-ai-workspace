/* UI V4 shell: owns workspace chrome, navigation and lightweight dashboard context. */
(() => {
  const VERSION = "20260811.1";
  const CURRENT_PROJECT_STORAGE = "zhilian_current_project_v1";
  const WORKSPACE_KEY_STORAGE = "zhilian_workspace_key_v1";
  const ACCOUNT_READY_EVENT = "zhilink:account-ready";
  const PROJECT_REFRESH_MS = 30000;
  const FORMAL_ORIGINS = new Set(["user", "project", "imported"]);
  const RESULT_KEYS = ["profile", "meeting", "contract", "policy", "match", "landing"];
  const MODULES = {
    home: { label: "工作首页", group: "工作台", icon: "home" },
    meeting: { label: "会议纪要", group: "业务处理", result: "会议纪要 · AI 生成结果", icon: "meeting" },
    contract: { label: "合同审阅", group: "业务处理", result: "合同风险 · AI 审阅结果", icon: "contract" },
    policy: { label: "政策助手", group: "业务处理", result: "政策方向 · AI 建议结果", icon: "policy" },
    match: { label: "供需协作", group: "业务处理", result: "供需协作 · AI 方案结果", icon: "match" },
    profile: { label: "企业档案", group: "资料与执行", result: "企业档案 · 生成结果", icon: "profile" },
    landing: { label: "实施计划", group: "资料与执行", result: "实施计划 · AI 生成结果", icon: "plan" },
    report: { label: "报告归档", group: "归档", result: "运营报告 · 汇总与导出", icon: "report" },
  };
  const ICONS = {
    menu: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
    down: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg>',
    project: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3.5 6.5h6.7l2 2h8.3v10.5h-17z"/><path d="M3.5 9h17"/></svg>',
    knowledge: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h6a3 3 0 0 1 3 3v13a3 3 0 0 0-3-3H5z"/><path d="M19 4h-2a3 3 0 0 0-3 3v13a3 3 0 0 1 3-3h2z"/></svg>',
    home: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10.5V20h13v-9.5M9 20v-6h6v6"/></svg>',
    meeting: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3.5h9l3 3V21H6z"/><path d="M15 3.5V7h3M9 12h6M9 16h4"/></svg>',
    contract: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3.5h9l3 3V21H6z"/><path d="M15 3.5V7h3M9 11h5M9 15h3"/><circle cx="15.5" cy="15.5" r="4"/></svg>',
    policy: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9h16M6 9V7l6-3 6 3v2M7 9v8M11 9v8M15 9v8M19 17H5v3h14z"/></svg>',
    match: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8.5 12.5 11 15a2.4 2.4 0 0 0 3.4 0l4.1-4.1"/><path d="m9.5 8.5 2-2a2.8 2.8 0 0 1 4 0l4 4-3 3"/></svg>',
    profile: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20V8h8v12M12 20V4h8v16"/><path d="M7 11h2M7 14h2M15 7h2M15 10h2M15 13h2"/></svg>',
    plan: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M7 3v4M17 3v4M3.5 9h17"/></svg>',
    report: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3.5h9l3 3V21H6z"/><path d="M15 3.5V7h3M9 17v-3M12 17v-6M15 17v-4"/></svg>',
    account: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="3.5"/><path d="M5 20a7 7 0 0 1 14 0"/></svg>',
    arrow: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M14 7l5 5-5 5"/></svg>',
  };

  let latestProjects = { items: [], total: 0 };
  let lastProjectSignature = "";
  let projectTimer = null;
  let bound = false;

  const byId = id => document.getElementById(id);
  const readJson = (raw, fallback) => { try { return raw ? JSON.parse(raw) : fallback; } catch (_) { return fallback; } };
  const setText = (element, value) => { if (element && element.textContent !== String(value)) element.textContent = String(value); };
  const safe = value => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  const notify = message => typeof toast === "function" ? toast(message) : console.info(message);

  function ensureStyles() {
    const assets = [
      ["ui-v4-shell", "ui-v4-shell.css"],
      ["ui-v4-navigation", "ui-v4-navigation.css"],
    ];
    assets.forEach(([key, file]) => {
      if (document.querySelector(`link[data-${key}]`)) return;
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = `/assets/${file}?v=${VERSION}`;
      link.setAttribute(`data-${key}`, "true");
      document.head.appendChild(link);
    });
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
    if (!target) { notify("该功能仍在初始化，请稍后重试。"); return false; }
    target.click();
    return true;
  }
  function currentProject() { return readJson(localStorage.getItem(CURRENT_PROJECT_STORAGE), null); }
  function resultState() {
    return {
      results: typeof state !== "undefined" ? state.results || {} : readJson(sessionStorage.getItem("zhilian_results"), {}),
      meta: typeof state !== "undefined" ? state.meta || {} : readJson(sessionStorage.getItem("zhilian_meta"), {}),
    };
  }
  function isFormalResult(key) {
    const external = window.ZHILINK_DATA_PROVENANCE?.isFormalResult;
    if (typeof external === "function") return external(key);
    const { results, meta } = resultState();
    return Boolean(results[key]) && FORMAL_ORIGINS.has(String(meta?.[key]?.origin || ""));
  }
  function accountLabel() {
    const text = byId("openAccountManager")?.textContent?.trim() || "登录 / 组织";
    return text === "登录 / 组织" ? text : text.split(" · ")[0]?.trim() || "企业账户";
  }
  function setSidebarOpen(open) {
    document.body.classList.toggle("ui-v4-sidebar-open", Boolean(open));
    document.querySelector(".sidebar")?.classList.toggle("ui-v4-open", Boolean(open));
    byId("uiV4MobileMenu")?.setAttribute("aria-expanded", String(Boolean(open)));
  }
  function closeAccountMenu() {
    const menu = byId("uiV4AccountMenu");
    if (menu) menu.hidden = true;
    byId("uiV4AccountToggle")?.setAttribute("aria-expanded", "false");
  }
  function openModelConfig() {
    const panel = byId("apiPanel");
    if (!panel) return false;
    panel.classList.remove("collapsed");
    document.body.classList.add("ui-v4-api-open");
    window.ZHILINK_UI_V4_RUNTIME?.schedule?.("model-open");
    return true;
  }

  function ensureTopNavigation() {
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
      topbar.insertBefore(mobile, topbar.firstChild);
    }
    if (!byId("uiV4TopNav")) {
      const nav = document.createElement("nav");
      nav.id = "uiV4TopNav";
      nav.className = "ui-v4-top-nav";
      nav.setAttribute("aria-label", "项目与账户");
      nav.innerHTML = `
        <button id="uiV4ProjectContext" class="ui-v4-project-context" type="button">
          <span class="ui-v4-project-icon">${ICONS.project}</span>
          <span class="ui-v4-project-copy"><small>当前项目</small><strong id="uiV4ProjectName">未选择项目</strong></span>
          <span id="uiV4ProjectMeta" class="ui-v4-project-meta">创建 / 打开</span>
        </button>
        <div class="ui-v4-account-wrap">
          <button id="uiV4AccountToggle" class="ui-v4-account-toggle" type="button" aria-expanded="false" aria-controls="uiV4AccountMenu">
            <span class="ui-v4-account-avatar">${ICONS.account}</span><span id="uiV4AccountLabel">企业账户</span>${ICONS.down}
          </button>
          <div id="uiV4AccountMenu" class="ui-v4-account-menu" hidden>
            <button type="button" data-ui-v4-account="account">账户与组织</button>
            <button type="button" data-ui-v4-account="identity">使用身份</button>
            <button type="button" data-ui-v4-account="api">模型配置</button>
            <button type="button" data-ui-v4-account="service">服务跟进</button>
            <hr />
            <button type="button" class="ui-v4-danger" data-ui-v4-account="clear">清空本次会话</button>
          </div>
        </div>`;
      topActions.appendChild(nav);
    }
  }

  function normalizeSidebar() {
    const nav = byId("navList");
    if (!nav) return;
    const groupLabels = { "资料与计划": "资料与执行", "输出归档": "归档", "运营总览": "工作台" };
    Array.from(nav.querySelectorAll(":scope > .nav-group-label")).forEach(group => {
      setText(group, groupLabels[group.textContent.trim()] || group.textContent.trim());
      group.classList.add("ui-v4-nav-group-label");
    });
    const home = nav.querySelector('button[data-section="home"]');
    if (home && !byId("uiV4WorkspaceGroup")) {
      const group = document.createElement("div");
      group.id = "uiV4WorkspaceGroup";
      group.className = "nav-group-label ui-v4-nav-group-label";
      group.textContent = "工作台";
      nav.insertBefore(group, home);
    }
    nav.querySelectorAll("button[data-section]").forEach(button => {
      const config = MODULES[button.dataset.section];
      if (!config) return;
      let label = button.querySelector(":scope > .ui-v4-nav-label");
      if (!label) {
        const textNode = Array.from(button.childNodes).find(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
        label = document.createElement("span");
        label.className = "ui-v4-nav-label";
        if (textNode) textNode.replaceWith(label); else button.appendChild(label);
      }
      setText(label, config.label);
      const holder = button.querySelector(":scope > span:not(.ui-v4-nav-label)");
      if (holder && holder.dataset.uiV4Icon !== "true") {
        holder.className = "ui-v4-nav-icon";
        holder.innerHTML = ICONS[config.icon] || ICONS.home;
        holder.dataset.uiV4Icon = "true";
      }
    });
  }

  function ensureSidebarSupport() {
    const sidebar = document.querySelector(".sidebar");
    if (!sidebar) return;
    let recent = byId("uiV4SidebarRecent");
    if (!recent) {
      recent = document.createElement("section");
      recent.id = "uiV4SidebarRecent";
      recent.className = "ui-v4-sidebar-recent";
      recent.innerHTML = `<div class="ui-v4-sidebar-recent-head"><strong>最近项目</strong><span id="uiV4SidebarProjectCount">0</span></div><div id="uiV4SidebarProjectList"><p class="ui-v4-sidebar-empty">正在读取项目…</p></div><button class="ui-v4-sidebar-all" type="button" id="uiV4SidebarAllProjects">查看全部项目 →</button>`;
      sidebar.appendChild(recent);
    }
    if (!byId("uiV4ResourceNavigation")) {
      const resource = document.createElement("section");
      resource.id = "uiV4ResourceNavigation";
      resource.className = "ui-v4-resource-navigation";
      resource.innerHTML = `<div class="nav-group-label ui-v4-nav-group-label">组织资源</div><button id="uiV4KnowledgeNav" class="ui-v4-resource-button" type="button"><span class="ui-v4-resource-icon">${ICONS.knowledge}</span><span class="ui-v4-resource-copy"><strong>组织知识库</strong><small>组织材料与内部知识</small></span></button>`;
      sidebar.insertBefore(resource, recent);
    }
    if (!byId("uiV4MobileBackdrop")) {
      const backdrop = document.createElement("div");
      backdrop.id = "uiV4MobileBackdrop";
      backdrop.className = "ui-v4-mobile-backdrop";
      document.body.appendChild(backdrop);
    }
  }

  function decorateBusinessPages() {
    Object.entries(MODULES).forEach(([id, config]) => {
      if (id === "home") return;
      const page = byId(id);
      const content = page?.querySelector(":scope > .content-card");
      const result = page?.querySelector(":scope > .result-panel");
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
        const labels = id === "report" ? ["汇总已有结果", "支持多格式导出", "不导出 API Key"]
          : id === "profile" ? ["可选上下文", "支持快速示例", "结果可归档"]
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

  function ensureHomePanels() {
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
    }
    if (!byId("uiV4PendingPanel")) {
      const pending = document.createElement("section");
      pending.id = "uiV4PendingPanel";
      pending.className = "ui-v4-home-panel";
      pending.innerHTML = `<div class="ui-v4-panel-head"><h3>需要你处理</h3><span id="uiV4PendingCount">0 项</span></div><div id="uiV4PendingList" class="ui-v4-pending-list"></div>`;
      grid.appendChild(pending);
    }
    if (!byId("uiV4UsagePanel")) {
      const usage = document.createElement("section");
      usage.id = "uiV4UsagePanel";
      usage.className = "ui-v4-home-panel ui-v4-usage-panel";
      usage.innerHTML = `<div class="ui-v4-panel-head"><h3>工作状态</h3><span>正式材料</span></div><div id="uiV4Metrics" class="ui-v4-metrics"></div><p id="uiV4UsageNote" class="ui-v4-usage-note"></p>`;
      grid.appendChild(usage);
    }
  }

  function collectPendingItems() {
    const items = [];
    const seen = new Set();
    const pattern = /(待确认|需确认|人工确认|尚未明确|未明确|待补充|待核实|需核实)/;
    const titles = typeof resultTitles !== "undefined" ? resultTitles : {};
    const { results } = resultState();
    RESULT_KEYS.forEach(key => {
      if (!isFormalResult(key)) return;
      String(results[key] || "").split(/\n+/).forEach(raw => {
        const text = raw.replace(/^[#>*\-\d.、\s]+/, "").replace(/\[[A-Z0-9-]+\]/g, "").replace(/\s+/g, " ").trim();
        if (!text || !pattern.test(text) || seen.has(text)) return;
        seen.add(text);
        items.push({ title: text.slice(0, 70), source: titles[key] || key });
      });
    });
    RESULT_KEYS.forEach(key => {
      if (!isFormalResult(key)) return;
      byId(`${key}Result`)?.querySelectorAll(".review-workflow-bar strong").forEach(node => {
        const text = node.textContent.trim();
        if (!/(待审核|退回|失效|尚未建立)/.test(text)) return;
        const title = `${titles[key] || "材料"}：${text}`;
        if (!seen.has(title)) { seen.add(title); items.push({ title, source: "人工复核" }); }
      });
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
      : '<p class="ui-v4-panel-empty">当前正式材料中没有识别到待确认事项。新材料生成后会自动更新。</p>';
    if (list.innerHTML !== html) list.innerHTML = html;
  }
  function reviewCounts() {
    let confirmed = 0; let pending = 0;
    RESULT_KEYS.forEach(key => {
      if (!isFormalResult(key)) return;
      byId(`${key}Result`)?.querySelectorAll(".review-workflow-bar strong").forEach(node => {
        const text = node.textContent || "";
        if (/(批准|已确认)/.test(text)) confirmed += 1;
        if (/(待审核|退回|失效|尚未建立)/.test(text)) pending += 1;
      });
    });
    return { confirmed, pending };
  }
  function renderUsage() {
    const metrics = byId("uiV4Metrics");
    const note = byId("uiV4UsageNote");
    if (!metrics || !note) return;
    const generated = typeof window.ZHILINK_DATA_PROVENANCE?.formalCount === "function" ? window.ZHILINK_DATA_PROVENANCE.formalCount() : RESULT_KEYS.filter(isFormalResult).length;
    const project = currentProject();
    const reviews = reviewCounts();
    const html = `<div class="ui-v4-metric"><strong>${generated}</strong><span>正式材料</span></div><div class="ui-v4-metric"><strong>${latestProjects.total || 0}</strong><span>可访问项目</span></div><div class="ui-v4-metric"><strong>${reviews.confirmed}</strong><span>已确认 / 批准</span></div><div class="ui-v4-metric"><strong>${reviews.pending}</strong><span>待复核状态</span></div>`;
    if (metrics.innerHTML !== html) metrics.innerHTML = html;
    setText(note, project ? `当前项目：${project.name} · v${project.lock_version}${project.status === "archived" ? " · 已归档" : ""}` : "当前未打开持久化项目。示例和旧会话材料不会进入正式统计。");
  }

  function syncProjectContext() {
    const project = currentProject();
    const source = byId("openProjectManager");
    const name = byId("uiV4ProjectName");
    const meta = byId("uiV4ProjectMeta");
    const button = byId("uiV4ProjectContext");
    if (!button || !name || !meta) return;
    if (!project) {
      setText(name, "未选择项目"); setText(meta, "创建 / 打开");
      button.classList.remove("has-project", "is-dirty", "is-archived");
      button.title = "创建或打开项目";
      return;
    }
    const dirty = (source?.textContent?.trim() || "").includes("未保存");
    const archived = project.status === "archived";
    setText(name, project.name || "当前项目");
    setText(meta, dirty ? "未保存" : archived ? "已归档" : `v${project.lock_version || 1}`);
    button.classList.add("has-project");
    button.classList.toggle("is-dirty", dirty);
    button.classList.toggle("is-archived", archived);
    button.title = dirty ? "当前项目有未保存更改" : "打开项目与版本管理";
  }
  function syncPageContext() {
    const section = document.querySelector(".page.active-page")?.id || document.querySelector("#navList button.active")?.dataset.section || "home";
    setText(byId("pageKicker"), MODULES[section]?.group || "工作台");
    const title = byId("pageTitle");
    if (title) title.dataset.uiV4Section = section;
    document.documentElement.dataset.zhilinkSection = section;
  }
  function syncKnowledgeNavigation() {
    const source = byId("openKnowledgeBase");
    const button = byId("uiV4KnowledgeNav");
    if (!button) return;
    const available = Boolean(source && !source.hidden);
    button.classList.toggle("is-locked", !available);
    button.setAttribute("aria-disabled", String(!available));
    button.title = available ? (source.title || "打开组织知识库") : "登录并选择组织后使用知识库";
    setText(button.querySelector("small"), available ? "组织材料与内部知识" : "登录并选择组织后启用");
  }

  function projectHeaders() {
    const organization = window.ZHILINK_ACCOUNT?.getActiveOrganization?.() || null;
    if (organization) return {};
    const key = ensureWorkspaceKey();
    return key ? { "X-Workspace-Key": key } : {};
  }
  async function fetchProjects() {
    try {
      const response = await fetch("/api/projects?limit=4&offset=0", { headers: projectHeaders(), credentials: "same-origin" });
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
    try { return new Date(value).toLocaleString([], { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }); } catch (_) { return ""; }
  }
  function renderSidebarProjects(failed = false) {
    const list = byId("uiV4SidebarProjectList");
    const count = byId("uiV4SidebarProjectCount");
    if (!list || !count) return;
    setText(count, latestProjects.total || 0);
    const signature = JSON.stringify({ failed, total: latestProjects.total, items: latestProjects.items.map(item => [item.id, item.name, item.lock_version, item.updated_at]) });
    if (signature === lastProjectSignature) return;
    lastProjectSignature = signature;
    if (failed) { list.innerHTML = '<p class="ui-v4-sidebar-empty">项目列表暂时不可用，可点击“查看全部项目”重试。</p>'; return; }
    if (!latestProjects.items.length) { list.innerHTML = '<p class="ui-v4-sidebar-empty">暂无已保存项目。创建项目后会显示在这里。</p>'; return; }
    list.innerHTML = latestProjects.items.slice(0, 3).map(item => `<button class="ui-v4-sidebar-project" type="button" data-ui-v4-project-id="${safe(item.id)}"><strong>${safe(item.name)}</strong><small>v${safe(item.lock_version)} · ${safe(projectTime(item.updated_at))}</small></button>`).join("");
  }
  function openProjectFromSidebar(projectId) {
    setSidebarOpen(false);
    if (!triggerExisting("openProjectManager")) return;
    let attempts = 0;
    const timer = window.setInterval(() => {
      attempts += 1;
      const button = document.querySelector(`[data-load-project="${CSS.escape(projectId)}"]`);
      if (button) { window.clearInterval(timer); button.click(); }
      else if (attempts > 12) window.clearInterval(timer);
    }, 180);
  }

  function bindControls() {
    if (bound) return;
    bound = true;
    document.addEventListener("click", event => {
      const project = event.target.closest?.("#uiV4ProjectContext");
      if (project) { triggerExisting("openProjectManager"); return; }
      const mobile = event.target.closest?.("#uiV4MobileMenu");
      if (mobile) { setSidebarOpen(!document.body.classList.contains("ui-v4-sidebar-open")); return; }
      if (event.target.closest?.("#uiV4MobileBackdrop")) { setSidebarOpen(false); return; }
      if (event.target.closest?.("#uiV4SidebarAllProjects")) { setSidebarOpen(false); triggerExisting("openProjectManager"); return; }
      const recentProject = event.target.closest?.("[data-ui-v4-project-id]");
      if (recentProject) { openProjectFromSidebar(recentProject.dataset.uiV4ProjectId); return; }
      if (event.target.closest?.("#uiV4KnowledgeNav")) {
        const source = byId("openKnowledgeBase");
        if (source && !source.hidden) source.click(); else triggerExisting("openAccountManager");
        return;
      }
      const toggle = event.target.closest?.("#uiV4AccountToggle");
      if (toggle) {
        event.stopPropagation();
        const menu = byId("uiV4AccountMenu");
        if (!menu) return;
        const opening = menu.hidden;
        menu.hidden = !opening;
        toggle.setAttribute("aria-expanded", String(opening));
        return;
      }
      const accountAction = event.target.closest?.("[data-ui-v4-account]");
      if (accountAction) {
        closeAccountMenu();
        const action = accountAction.dataset.uiV4Account;
        if (action === "account") triggerExisting("openAccountManager");
        else if (action === "identity") triggerExisting("openIdentity");
        else if (action === "api") openModelConfig();
        else if (action === "service") triggerExisting("openServiceWorkflow");
        else if (action === "clear") triggerExisting("clearAll");
        return;
      }
      const menu = byId("uiV4AccountMenu");
      const wrap = document.querySelector(".ui-v4-account-wrap");
      if (menu && wrap && !menu.hidden && !wrap.contains(event.target)) closeAccountMenu();
      if (event.target.closest?.(".nav button")) setSidebarOpen(false);
    });
    document.addEventListener("keydown", event => {
      if (event.key !== "Escape") return;
      closeAccountMenu(); setSidebarOpen(false);
    });
    window.addEventListener("storage", event => {
      if ([CURRENT_PROJECT_STORAGE, WORKSPACE_KEY_STORAGE].includes(event.key)) {
        fetchProjects();
        window.ZHILINK_UI_V4_RUNTIME?.schedule?.("project-storage");
      }
    });
    [window, document].forEach(target => target.addEventListener(ACCOUNT_READY_EVENT, () => {
      fetchProjects();
      window.ZHILINK_UI_V4_RUNTIME?.schedule?.("account-ready");
    }));
  }

  function apply() {
    ensureStyles();
    if (!document.body) return;
    document.body.classList.add("ui-v4-shell");
    document.documentElement.dataset.zhilinkUi = "v4";
    ensureTopNavigation();
    normalizeSidebar();
    ensureSidebarSupport();
    ensureHomePanels();
    decorateBusinessPages();
    decorateHomeCards();
    setText(byId("uiV4AccountLabel"), accountLabel());
    syncProjectContext();
    syncPageContext();
    syncKnowledgeNavigation();
    renderPending();
    renderUsage();
    const mobile = byId("uiV4MobileMenu");
    if (mobile) {
      const open = document.body.classList.contains("ui-v4-sidebar-open");
      mobile.setAttribute("aria-expanded", String(open));
      mobile.setAttribute("aria-label", open ? "关闭导航" : "打开导航");
    }
    window.ZHILINK_UI_V4_SHELL_READY = true;
  }

  function start() {
    ensureWorkspaceKey();
    apply();
    bindControls();
    window.ZHILINK_UI_V4_RUNTIME?.subscribe?.(apply, { immediate: false });
    fetchProjects();
    projectTimer = window.setInterval(fetchProjects, PROJECT_REFRESH_MS);
    window.addEventListener("beforeunload", () => projectTimer && window.clearInterval(projectTimer), { once: true });
  }

  window.ZHILINK_UI_V4_SHELL = {
    openModelConfig,
    closeAccountMenu,
    setSidebarOpen,
    refresh: () => window.ZHILINK_UI_V4_RUNTIME?.schedule?.("shell-refresh"),
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
