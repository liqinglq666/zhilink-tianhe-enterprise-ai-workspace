/* UI V4 final QA: responsive and accessibility guardrails without owning business state. */
(() => {
  const VERSION = "20260811.1";
  const PAGE_NAV_SELECTOR = "#navList button[data-section], [data-goto]";
  const SCROLLABLE_SELECTOR = ".result-section-content, .structured-table-wrap";
  let keyboardNavigationPending = false;

  function ensureStyles() {
    if (document.querySelector("link[data-ui-v4-final-qa]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `/assets/ui-v4-final-qa.css?v=${VERSION}`;
    link.dataset.uiV4FinalQa = "true";
    document.head.appendChild(link);
  }
  function ensureSkipLink() {
    const main = document.querySelector("main.main");
    if (!(main instanceof HTMLElement)) return;
    if (!main.id) main.id = "mainContent";
    if (!main.hasAttribute("tabindex")) main.setAttribute("tabindex", "-1");
    if (!main.hasAttribute("aria-label")) main.setAttribute("aria-label", "主要工作区");
    let link = document.getElementById("uiV4SkipLink");
    if (!(link instanceof HTMLAnchorElement)) {
      link = document.createElement("a");
      link.id = "uiV4SkipLink";
      link.className = "ui-v4-skip-link";
      link.href = `#${main.id}`;
      link.textContent = "跳到主内容";
      document.body.insertBefore(link, document.body.firstChild);
      link.addEventListener("click", () => requestAnimationFrame(() => main.focus({ preventScroll: true })));
    }
  }
  function ensureSidebarSemantics() {
    const sidebar = document.querySelector(".sidebar");
    if (sidebar instanceof HTMLElement && !sidebar.id) sidebar.id = "primarySidebar";
    document.getElementById("navList")?.querySelectorAll("button[data-section]").forEach(button => {
      if (button.classList.contains("active")) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
    const mobile = document.getElementById("uiV4MobileMenu");
    if (mobile instanceof HTMLButtonElement && sidebar instanceof HTMLElement) {
      mobile.setAttribute("aria-controls", sidebar.id);
      mobile.setAttribute("aria-label", document.body.classList.contains("ui-v4-sidebar-open") ? "关闭主导航" : "打开主导航");
    }
  }
  function ensureTopbarSemantics() {
    const title = document.getElementById("pageTitle");
    if (title instanceof HTMLElement && !title.hasAttribute("tabindex")) title.setAttribute("tabindex", "-1");
    const project = document.getElementById("uiV4ProjectContext");
    if (project instanceof HTMLButtonElement) {
      const name = document.getElementById("uiV4ProjectName")?.textContent?.trim() || "未选择项目";
      const meta = document.getElementById("uiV4ProjectMeta")?.textContent?.trim() || "";
      project.setAttribute("aria-label", `当前项目：${name}${meta ? `，${meta}` : ""}。打开项目与版本管理`);
    }
    const account = document.getElementById("uiV4AccountToggle");
    const menu = document.getElementById("uiV4AccountMenu");
    if (account instanceof HTMLButtonElement && menu instanceof HTMLElement) account.setAttribute("aria-controls", menu.id);
  }
  function ensureBaseInteractiveSemantics() {
    const identity = document.getElementById("identityChip");
    if (identity instanceof HTMLElement && !identity.hidden) {
      identity.setAttribute("role", "button");
      identity.setAttribute("tabindex", "0");
      identity.setAttribute("aria-label", `当前使用身份：${document.getElementById("identityDisplay")?.textContent?.trim() || "未设置"}。打开身份设置`);
    }
  }
  function decorateScrollableRegions() {
    document.querySelectorAll(SCROLLABLE_SELECTOR).forEach(region => {
      if (!(region instanceof HTMLElement)) return;
      const overflow = region.scrollWidth > region.clientWidth + 2;
      if (overflow) {
        region.dataset.uiV4KeyboardScroll = "true";
        region.setAttribute("tabindex", "0");
        region.setAttribute("role", "region");
        if (!region.hasAttribute("aria-label")) region.setAttribute("aria-label", "可横向滚动的内容区域");
      } else if (region.dataset.uiV4KeyboardScroll === "true") {
        delete region.dataset.uiV4KeyboardScroll;
        region.removeAttribute("tabindex");
        region.removeAttribute("role");
        if (region.getAttribute("aria-label") === "可横向滚动的内容区域") region.removeAttribute("aria-label");
      }
    });
  }
  function syncViewportClass() {
    const width = window.innerWidth;
    const viewport = width <= 360 ? "compact-360" : width <= 390 ? "compact-390" : width <= 768 ? "mobile" : width <= 1024 ? "tablet" : width <= 1280 ? "desktop-compact" : "desktop";
    document.documentElement.dataset.uiV4Viewport = viewport;
  }
  function focusPageContextAfterKeyboardNavigation() {
    if (!keyboardNavigationPending) return;
    keyboardNavigationPending = false;
    const title = document.getElementById("pageTitle");
    if (title instanceof HTMLElement) {
      title.focus({ preventScroll: true });
      title.scrollIntoView({ block: "nearest", behavior: "auto" });
    }
  }
  function sync() {
    ensureSkipLink();
    ensureSidebarSemantics();
    ensureTopbarSemantics();
    ensureBaseInteractiveSemantics();
    decorateScrollableRegions();
    syncViewportClass();
    document.body.classList.add("ui-v4-final-qa");
    window.ZHILINK_UI_V4_FINAL_QA_READY = true;
    if (keyboardNavigationPending) requestAnimationFrame(focusPageContextAfterKeyboardNavigation);
  }
  function handleKeydown(event) {
    document.body.classList.add("ui-v4-keyboard-user");
    const identity = event.target.closest?.("#identityChip[role='button']");
    if (identity && (event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      identity.click();
      return;
    }
    if ((event.key === "Enter" || event.key === " ") && event.target.closest?.(PAGE_NAV_SELECTOR)) keyboardNavigationPending = true;
  }
  function handleClick(event) {
    if (event.detail === 0 && event.target.closest?.(PAGE_NAV_SELECTOR)) {
      keyboardNavigationPending = true;
      window.ZHILINK_UI_V4_RUNTIME?.schedule?.("keyboard-navigation");
    }
  }
  function start() {
    ensureStyles();
    sync();
    window.ZHILINK_UI_V4_RUNTIME?.subscribe?.(sync, { immediate: false });
    document.addEventListener("keydown", handleKeydown, true);
    document.addEventListener("click", handleClick, true);
    document.addEventListener("pointerdown", () => document.body.classList.remove("ui-v4-keyboard-user"), true);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
