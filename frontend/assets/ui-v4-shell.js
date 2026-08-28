/* UI V4 shell: owns workspace chrome, navigation, project and account context. */
(() => {
  const contracts = window.ZHILINK_WORKSPACE_CONTRACTS;
  const ICONS = window.ZHILINK_UI_V4_ICONS;
  const HELPERS = window.ZHILINK_UI_V4_HELPERS;
  if (!contracts || !ICONS || !HELPERS) throw new Error("Workspace runtime, icons and helpers must load before shell.");

  const CURRENT_PROJECT_STORAGE = contracts.storage.currentProject;
  const WORKSPACE_KEY_STORAGE = contracts.storage.workspaceKey;
  const ACCOUNT_READY_EVENT = contracts.events.accountReady;
  const PROJECT_CHANGED_EVENT = contracts.events.projectChanged;
  const MODULES = contracts.modules;
  const { readJson, setText, escapeHtml: safe } = HELPERS;
  const MOBILE_SIDEBAR_QUERY = window.matchMedia?.("(max-width: 1020px)") || null;

  let latestProjects = { items: [], total: 0 };
  let lastProjectSignature = "";
  let pendingProjectId = "";
  let pendingMobileNavKey = "";
  let bound = false;

  const byId = id => document.getElementById(id);
  const notify = message => typeof toast === "function" ? toast(message) : console.info(message);
  const focusSoon = target => window.requestAnimationFrame(() => target?.focus?.({ preventScroll: true }));
  const isMobileSidebar = () => MOBILE_SIDEBAR_QUERY ? MOBILE_SIDEBAR_QUERY.matches : window.innerWidth <= 1020;

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
  function syncSidebarAccessibility() {
    const sidebar = document.querySelector(".sidebar");
    if (!sidebar) return;
    if (!isMobileSidebar()) {
      sidebar.removeAttribute("inert");
      sidebar.removeAttribute("aria-hidden");
      return;
    }
    const open = document.body.classList.contains("ui-v4-sidebar-open");
    if (!open && sidebar.contains(document.activeElement)) {
      (byId("uiV4MobileMenu") || byId("mainContent"))?.focus?.({ preventScroll: true });
    }
    sidebar.toggleAttribute("inert", !open);
    sidebar.setAttribute("aria-hidden", String(!open));
  }
  function setSidebarOpen(open, focusAfterClose = null) {
    const shouldOpen = Boolean(open) && isMobileSidebar();
    if (!shouldOpen && focusAfterClose) focusAfterClose.focus?.({ preventScroll: true });
    document.body.classList.toggle("ui-v4-sidebar-open", shouldOpen);
    document.querySelector(".sidebar")?.classList.toggle("ui-v4-open", shouldOpen);
    byId("uiV4MobileMenu")?.setAttribute("aria-expanded", String(shouldOpen));
    syncSidebarAccessibility();
    if (shouldOpen) {
      focusSoon(document.querySelector("#navList button.active") || document.querySelector("#navList button"));
    } else if (focusAfterClose) {
      focusSoon(focusAfterClose);
    }
  }
  function syncSidebarViewport() {
    if (!isMobileSidebar()) {
      document.body.classList.remove("ui-v4-sidebar-open");
      document.querySelector(".sidebar")?.classList.remove("ui-v4-open");
      byId("uiV4MobileMenu")?.setAttribute("aria-expanded", "false");
    }
    syncSidebarAccessibility();
  }
  function closeAccountMenu(returnFocus = false) {
    const menu = byId("uiV4AccountMenu");
    if (menu) menu.hidden = true;
    const toggle = byId("uiV4AccountToggle");
    toggle?.setAttribute("aria-expanded", "false");
    if (returnFocus) focusSoon(toggle);
  }
  function openModelConfig() {
    const drawer = window.ZHILINK_API_DRAWER_V4;
    if (!drawer || typeof drawer.open !== "function") {
      notify("AI 服务设置仍在初始化，请稍后重试。");
      return false;
    }
    drawer.open();
    return true;
  }

  function syncSidebarPresentation() {
    const nav = byId("navList");
    if (!nav) return;
    nav.querySelectorAll("button[data-section]").forEach(button => {
      const config = MODULES[button.dataset.section];
      const label = button.querySelector(":scope > .ui-v4-nav-label");
      if (!config || !label) return;
      setText(label, config.label);
      const holder = button.querySelector(":scope > .ui-v4-nav-icon");
      if (holder && holder.dataset.uiV4Icon !== "true") {
        holder.innerHTML = ICONS[config.icon] || ICONS.home;
        holder.dataset.uiV4Icon = "true";
      }
    });
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
      if (mobile) { setSidebarOpen(!document.body.classList.contains("ui-v4-sidebar-open"), mobile); return; }
      if (event.target.closest?.("#uiV4MobileBackdrop")) { setSidebarOpen(false, byId("uiV4MobileMenu")); return; }
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
        if (!opening) {
          closeAccountMenu(true);
          return;
        }
        menu.hidden = false;
        toggle.setAttribute("aria-expanded", "true");
        focusSoon(menu.querySelector("button:not([disabled])"));
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
      const navButton = event.target.closest?.(".nav button");
      if (navButton && isMobileSidebar()) {
        const title = byId("pageTitle");
        setSidebarOpen(false);
        if (!pendingMobileNavKey) title?.focus?.({ preventScroll: true });
      }
    });
    document.addEventListener("keydown", event => {
      const navButton = event.target.closest?.(".nav button");
      if (navButton && isMobileSidebar() && ["Enter", " "].includes(event.key)) {
        event.preventDefault();
        pendingMobileNavKey = event.key;
        navButton.click();
        return;
      }
      if (event.key !== "Escape") return;
      const accountMenu = byId("uiV4AccountMenu");
      if (accountMenu && !accountMenu.hidden) {
        event.preventDefault();
        closeAccountMenu(true);
        return;
      }
      if (document.body.classList.contains("ui-v4-sidebar-open")) {
        event.preventDefault();
        setSidebarOpen(false, byId("uiV4MobileMenu"));
      }
    });
    document.addEventListener("keyup", event => {
      if (!pendingMobileNavKey || event.key !== pendingMobileNavKey) return;
      event.preventDefault();
      pendingMobileNavKey = "";
      byId("pageTitle")?.focus?.({ preventScroll: true });
    });
    window.addEventListener("blur", () => { pendingMobileNavKey = ""; });
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
    MOBILE_SIDEBAR_QUERY?.addEventListener?.("change", syncSidebarViewport);
  }

  function apply() {
    if (!document.body) return;
    document.body.classList.add("ui-v4-shell");
    document.documentElement.dataset.zhilinkUi = "v4";
    syncSidebarPresentation();
    setText(byId("uiV4AccountLabel"), accountLabel());
    syncProjectContext();
    syncPageContext();
    syncKnowledgeNavigation();
    resolvePendingProjectOpen();
    syncSidebarAccessibility();
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
    syncSidebarViewport();
    window.ZHILINK_UI_V4_RUNTIME?.subscribe?.(apply, { immediate: false });
    if (window.ACCOUNT_ACCESS_READY) fetchProjects();
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