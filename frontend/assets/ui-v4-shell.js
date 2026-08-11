/* UI V4 shell: owns workspace chrome, navigation, project and account context. */
(() => {
  const VERSION = "20260811.2";
  const contracts = window.ZHILINK_WORKSPACE_CONTRACTS;
  const ICONS = window.ZHILINK_UI_V4_ICONS;
  if (!contracts || !ICONS) throw new Error("Workspace runtime and icons must load before shell.");

  const CURRENT_PROJECT_STORAGE = contracts.storage.currentProject;
  const WORKSPACE_KEY_STORAGE = contracts.storage.workspaceKey;
  const ACCOUNT_READY_EVENT = contracts.events.accountReady;
  const PROJECT_CHANGED_EVENT = contracts.events.projectChanged;
  const MODULES = {
    home: { label: "工作首页", group: "工作台", icon: "home" },
    meeting: { label: "会议纪要", group: "业务处理", icon: "meeting" },
    contract: { label: "合同审阅", group: "业务处理", icon: "contract" },
    policy: { label: "政策助手", group: "业务处理", icon: "policy" },
    match: { label: "供需协作", group: "业务处理", icon: "match" },
    profile: { label: "企业档案", group: "资料与执行", icon: "profile" },
    landing: { label: "实施计划", group: "资料与执行", icon: "plan" },
    report: { label: "报告归档", group: "归档", icon: "report" },
  };

  let latestProjects = { items: [], total: 0 };
  let lastProjectSignature = "";
  let pendingProjectId = "";
  let bound = false;

  const byId = id => document.getElementById(id);
  const readJson = (raw, fallback) => { try { return raw ? JSON.parse(raw) : fallback; } catch (_) { return fallback; } };
  const setText = (element, value) => { if (element && element.textContent !== String(value)) element.textContent = String(value); };
  const safe = value => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
  const notify = message => typeof toast === "function" ? toast(message) : console.info(message);

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
    if (!target) { notify("该功能仍在初始化，请稍后重试。"); return false; }
    target.click();
    return true;
  }
  function currentProject() { return readJson(localStorage.getItem(CURRENT_PROJECT_STORAGE), null); }
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
    window.ZHILINK_UI_V4_RUNTIME?.schedule?.("projects-refreshed");
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
    pendingProjectId = String(projectId || "");
    if (!pendingProjectId || !triggerExisting("openProjectManager")) {
      pendingProjectId = "";
      return;
    }
    window.ZHILINK_UI_V4_RUNTIME?.schedule?.("project-open");
  }
  function resolvePendingProjectOpen() {
    if (!pendingProjectId) return;
    const button = document.querySelector(`[data-load-project="${CSS.escape(pendingProjectId)}"]`);
    if (!button) return;
    pendingProjectId = "";
    button.click();
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
    window.addEventListener(PROJECT_CHANGED_EVENT, fetchProjects);
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
    setText(byId("uiV4AccountLabel"), accountLabel());
    syncProjectContext();
    syncPageContext();
    syncKnowledgeNavigation();
    resolvePendingProjectOpen();
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
  }

  window.ZHILINK_UI_V4_SHELL = {
    openModelConfig,
    closeAccountMenu,
    setSidebarOpen,
    projectCount: () => Number(latestProjects.total || 0),
    refresh: () => window.ZHILINK_UI_V4_RUNTIME?.schedule?.("shell-refresh"),
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
