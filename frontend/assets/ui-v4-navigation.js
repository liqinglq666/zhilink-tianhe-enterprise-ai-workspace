/* UI V4 navigation: one navigation system, one project context, one account menu. */
(() => {
  const VERSION = "20260810.1";
  const CURRENT_PROJECT_STORAGE = "zhilian_current_project_v1";
  const SECTION_GROUPS = {
    home: "工作台",
    meeting: "业务处理",
    contract: "业务处理",
    policy: "业务处理",
    match: "业务处理",
    profile: "资料与执行",
    landing: "资料与执行",
    report: "归档",
  };
  const SECTION_LABELS = {
    home: "工作首页",
    meeting: "会议纪要",
    contract: "合同审阅",
    policy: "政策助手",
    match: "供需协作",
    profile: "企业档案",
    landing: "实施计划",
    report: "报告归档",
  };
  const ICONS = {
    project: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3.5 6.5h6.7l2 2h8.3v10.5h-17z"/><path d="M3.5 9h17"/></svg>',
    knowledge: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h6a3 3 0 0 1 3 3v13a3 3 0 0 0-3-3H5z"/><path d="M19 4h-2a3 3 0 0 0-3 3v13a3 3 0 0 1 3-3h2z"/></svg>',
  };

  let observer = null;
  let queued = false;

  function readJson(raw, fallback) {
    try { return raw ? JSON.parse(raw) : fallback; } catch (_) { return fallback; }
  }

  function setText(element, value) {
    if (element && element.textContent !== String(value)) element.textContent = String(value);
  }

  function ensureStyles() {
    if (document.querySelector("link[data-ui-v4-navigation]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `/assets/ui-v4-navigation.css?v=${VERSION}`;
    link.dataset.uiV4Navigation = "true";
    document.head.appendChild(link);
  }

  function triggerExisting(id) {
    const target = document.getElementById(id);
    if (!target) return false;
    target.click();
    return true;
  }

  function activeSection() {
    return document.querySelector(".page.active-page")?.id
      || document.querySelector("#navList button.active")?.dataset.section
      || "home";
  }

  function currentProject() {
    return readJson(localStorage.getItem(CURRENT_PROJECT_STORAGE), null);
  }

  function replaceDirectText(button, text) {
    if (!button) return;
    let label = button.querySelector(":scope > .ui-v4-nav-label");
    if (!label) {
      const textNode = Array.from(button.childNodes).find(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
      if (textNode) {
        label = document.createElement("span");
        label.className = "ui-v4-nav-label";
        textNode.replaceWith(label);
      } else {
        label = document.createElement("span");
        label.className = "ui-v4-nav-label";
        button.appendChild(label);
      }
    }
    setText(label, text);
  }

  function normalizeSidebarGroups() {
    const nav = document.getElementById("navList");
    if (!nav) return;

    const home = nav.querySelector('button[data-section="home"]');
    if (home && !document.getElementById("uiV4WorkspaceGroup")) {
      const group = document.createElement("div");
      group.id = "uiV4WorkspaceGroup";
      group.className = "nav-group-label ui-v4-nav-group-label";
      group.textContent = "工作台";
      nav.insertBefore(group, home);
    }

    nav.querySelectorAll("button[data-section]").forEach(button => {
      const section = button.dataset.section || "";
      replaceDirectText(button, SECTION_LABELS[section] || section);
      button.dataset.uiV4Nav = "true";
    });

    const groups = Array.from(nav.querySelectorAll(":scope > .nav-group-label"));
    groups.forEach(group => {
      const text = group.textContent.trim();
      if (text === "资料与计划") setText(group, "资料与执行");
      if (text === "输出归档") setText(group, "归档");
      group.classList.add("ui-v4-nav-group-label");
    });
  }

  function buildKnowledgeNavigation() {
    const sidebar = document.querySelector(".sidebar");
    const recent = document.getElementById("liveSidebarRecent");
    if (!sidebar || !recent) return;

    if (!document.getElementById("uiV4ResourceNavigation")) {
      const resource = document.createElement("section");
      resource.id = "uiV4ResourceNavigation";
      resource.className = "ui-v4-resource-navigation";
      resource.innerHTML = `
        <div class="nav-group-label ui-v4-nav-group-label">组织资源</div>
        <button id="uiV4KnowledgeNav" class="ui-v4-resource-button" type="button">
          <span class="ui-v4-resource-icon">${ICONS.knowledge}</span>
          <span class="ui-v4-resource-copy"><strong>组织知识库</strong><small>组织材料与内部知识</small></span>
        </button>`;
      sidebar.insertBefore(resource, recent);
      document.getElementById("uiV4KnowledgeNav")?.addEventListener("click", () => {
        const source = document.getElementById("openKnowledgeBase");
        if (source && !source.hidden) source.click();
        else triggerExisting("openAccountManager");
      });
    }

    syncKnowledgeNavigation();
  }

  function syncKnowledgeNavigation() {
    const source = document.getElementById("openKnowledgeBase");
    const button = document.getElementById("uiV4KnowledgeNav");
    if (!button) return;
    const available = Boolean(source && !source.hidden);
    button.classList.toggle("is-locked", !available);
    button.setAttribute("aria-disabled", String(!available));
    button.title = available ? (source.title || "打开组织知识库") : "登录并选择组织后使用知识库";
    const note = button.querySelector("small");
    setText(note, available ? "组织材料与内部知识" : "登录并选择组织后启用");
  }

  function simplifyTopNavigation() {
    const nav = document.getElementById("liveTopNav");
    if (!nav) return;

    ["liveProjectNav", "liveKnowledgeNav", "liveReportNav"].forEach(id => {
      document.getElementById(id)?.classList.add("ui-v4-top-redundant");
    });

    if (!document.getElementById("uiV4ProjectContext")) {
      const project = document.createElement("button");
      project.id = "uiV4ProjectContext";
      project.className = "ui-v4-project-context";
      project.type = "button";
      project.innerHTML = `
        <span class="ui-v4-project-icon">${ICONS.project}</span>
        <span class="ui-v4-project-copy">
          <small>当前项目</small>
          <strong id="uiV4ProjectName">未选择项目</strong>
        </span>
        <span id="uiV4ProjectMeta" class="ui-v4-project-meta">创建 / 打开</span>`;
      const account = nav.querySelector(".live-account-wrap");
      nav.insertBefore(project, account || nav.firstChild);
      project.addEventListener("click", () => triggerExisting("openProjectManager"));
    }

    const account = nav.querySelector(".live-account-wrap");
    account?.classList.add("ui-v4-account-context");
    const toggle = document.getElementById("liveAccountToggle");
    if (toggle) toggle.setAttribute("aria-label", "账户、组织与设置");

    const menu = document.getElementById("liveAccountMenu");
    if (menu) {
      menu.classList.add("ui-v4-account-menu");
      const labels = {
        account: "账户与组织",
        identity: "使用身份",
        api: "模型配置",
        clear: "清空本次会话",
      };
      menu.querySelectorAll("[data-live-account]").forEach(button => {
        setText(button, labels[button.dataset.liveAccount] || button.textContent.trim());
      });
    }

    syncProjectContext();
  }

  function syncProjectContext() {
    const project = currentProject();
    const source = document.getElementById("openProjectManager");
    const name = document.getElementById("uiV4ProjectName");
    const meta = document.getElementById("uiV4ProjectMeta");
    const button = document.getElementById("uiV4ProjectContext");
    if (!button || !name || !meta) return;

    if (!project) {
      setText(name, "未选择项目");
      setText(meta, "创建 / 打开");
      button.classList.remove("has-project", "is-dirty", "is-archived");
      button.title = "创建或打开项目";
      return;
    }

    const sourceText = source?.textContent?.trim() || "";
    const dirty = sourceText.includes("未保存");
    const archived = project.status === "archived";
    setText(name, project.name || "当前项目");
    setText(meta, dirty ? "未保存" : archived ? "已归档" : `v${project.lock_version || 1}`);
    button.classList.add("has-project");
    button.classList.toggle("is-dirty", dirty);
    button.classList.toggle("is-archived", archived);
    button.title = dirty ? "当前项目有未保存更改" : "打开项目与版本管理";
  }

  function syncPageContext() {
    const section = activeSection();
    const group = SECTION_GROUPS[section] || "工作台";
    const kicker = document.getElementById("pageKicker");
    const title = document.getElementById("pageTitle");
    const subtitle = document.getElementById("pageSubtitle");

    setText(kicker, group);
    if (title) title.dataset.uiV4Section = section;
    if (subtitle) subtitle.dataset.uiV4Context = "true";
    document.documentElement.dataset.zhilinkSection = section;
  }

  function syncMobileSidebarState() {
    const mobile = document.getElementById("liveMobileMenu");
    if (!mobile) return;
    const open = document.body.classList.contains("live-sidebar-open");
    mobile.setAttribute("aria-expanded", String(open));
  }

  function apply() {
    ensureStyles();
    if (!document.body) return;
    document.body.classList.add("ui-v4-navigation");
    document.documentElement.dataset.zhilinkNavigation = "v4";
    normalizeSidebarGroups();
    buildKnowledgeNavigation();
    simplifyTopNavigation();
    syncPageContext();
    syncKnowledgeNavigation();
    syncProjectContext();
    syncMobileSidebarState();
    window.ZHILINK_UI_V4_NAVIGATION_READY = true;
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
        if (mutation.type === "attributes") {
          return ["class", "hidden", "aria-hidden"].includes(mutation.attributeName);
        }
        return mutation.addedNodes.length || mutation.removedNodes.length;
      });
      if (relevant) queueApply();
    });
    observer.observe(document.body, {
      subtree: true,
      childList: true,
      characterData: true,
      attributes: true,
      attributeFilter: ["class", "hidden", "aria-hidden"],
    });
  }

  const start = () => {
    apply();
    installObserver();
    window.addEventListener("storage", event => {
      if (event.key === CURRENT_PROJECT_STORAGE) queueApply();
    });
    window.addEventListener("zhilink:account-ready", queueApply);
    window.addEventListener("zhilink:workspace-state-change", queueApply);
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
