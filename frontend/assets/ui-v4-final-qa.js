/* UI V4 final QA: canonical responsive, workspace and accessibility presentation controller. */
(() => {
  const contracts = window.ZHILINK_WORKSPACE_CONTRACTS;
  const ICONS = window.ZHILINK_UI_V4_ICONS;
  if (!contracts || !ICONS) throw new Error("Workspace runtime and icons must load before final QA.");

  const PAGE_NAV_SELECTOR = "#navList button[data-section], [data-goto]";
  const SCROLLABLE_SELECTOR = ".result-section-content, .structured-table-wrap";
  const MOBILE_BREAKPOINT = 1020;
  const SHARED_MODULES = contracts.modules;
  let keyboardNavigationPending = false;
  let started = false;
  let resizeFrame = 0;

  function moduleMeta(id) {
    if (id === "report") return ["汇总已有结果", "支持多格式导出", "敏感设置不会导出"];
    if (id === "profile") return ["补充企业背景", "支持快速填写", "结果可归档"];
    return ["智能辅助整理", "人工复核后使用", "结果可归档"];
  }

  function decorateBusinessWorkspace() {
    document.documentElement.dataset.zhilinkWorkspace = "v4";
    document.querySelectorAll(".ui-v4-business-page[id]").forEach(page => {
      const id = page.id;
      const shared = SHARED_MODULES[id];
      const input = page.querySelector(":scope > .content-card");
      if (!shared || !input) return;

      const head = input.querySelector(".section-head");
      const iconHolder = head?.querySelector(":scope > span");
      if (iconHolder && iconHolder.dataset.uiV4Icon !== "true") {
        iconHolder.innerHTML = ICONS[shared.icon] || ICONS.home;
        iconHolder.dataset.uiV4Icon = "true";
        iconHolder.setAttribute("aria-hidden", "true");
      }

      if (head && !input.querySelector(".ui-v4-module-meta")) {
        const meta = document.createElement("div");
        meta.className = "ui-v4-module-meta";
        moduleMeta(id).forEach(label => {
          const item = document.createElement("span");
          item.textContent = label;
          meta.appendChild(item);
        });
        head.insertAdjacentElement("afterend", meta);
      }

      input.querySelectorAll("textarea").forEach(textarea => textarea.setAttribute("spellcheck", "false"));
      input.querySelectorAll(".sticky-actions button.primary").forEach(button => {
        if (button.dataset.uiV4Arrow === "true") return;
        button.insertAdjacentHTML("beforeend", ICONS.arrow);
        button.dataset.uiV4Arrow = "true";
      });
    });
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
    const sidebar = document.getElementById("primarySidebar") || document.querySelector(".sidebar");
    if (!(sidebar instanceof HTMLElement)) return;
    if (!sidebar.id) sidebar.id = "primarySidebar";

    document.getElementById("navList")?.querySelectorAll("button[data-section]").forEach(button => {
      if (button.classList.contains("active")) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });

    const mobile = document.getElementById("uiV4MobileMenu");
    if (mobile instanceof HTMLButtonElement) {
      const open = document.body.classList.contains("ui-v4-sidebar-open");
      mobile.setAttribute("aria-controls", sidebar.id);
      mobile.setAttribute("aria-label", open ? "关闭主导航" : "打开主导航");
      mobile.setAttribute("aria-expanded", open ? "true" : "false");
    }

    if (window.innerWidth <= MOBILE_BREAKPOINT) {
      sidebar.setAttribute("aria-hidden", document.body.classList.contains("ui-v4-sidebar-open") ? "false" : "true");
    } else {
      sidebar.removeAttribute("aria-hidden");
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
    if (account instanceof HTMLButtonElement && menu instanceof HTMLElement) {
      account.setAttribute("aria-controls", menu.id);
      account.setAttribute("aria-haspopup", "menu");
      menu.setAttribute("role", "menu");
      menu.querySelectorAll("button").forEach(button => button.setAttribute("role", "menuitem"));
    }

    document.querySelectorAll(".sticky-actions, .ui-v4-form-actions").forEach(actions => {
      if (!actions.getAttribute("aria-label")) actions.setAttribute("aria-label", "当前页面操作");
    });
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

  function markTaskHierarchy() {
    document.querySelectorAll("#home .module-card[data-tool-key]").forEach(card => {
      card.dataset.productTier = card.classList.contains("ui-v4-secondary-task") ? "utility" : "primary";
    });
  }

  function syncViewportMetrics() {
    const visualHeight = Math.round(window.visualViewport?.height || window.innerHeight || 0);
    const visualWidth = Math.round(window.visualViewport?.width || window.innerWidth || 0);
    if (visualHeight > 0) document.documentElement.style.setProperty("--ui4-visual-height", `${visualHeight}px`);
    if (visualWidth > 0) document.documentElement.style.setProperty("--ui4-visual-width", `${visualWidth}px`);

    const width = window.innerWidth;
    const viewport = width <= 360 ? "compact-360" : width <= 390 ? "compact-390" : width <= 768 ? "mobile" : width <= 1024 ? "tablet" : width <= 1280 ? "desktop-compact" : "desktop";
    document.documentElement.dataset.uiV4Viewport = viewport;
    document.documentElement.dataset.uiV4Height = visualHeight <= 700 ? "short" : visualHeight <= 820 ? "compact" : "regular";
  }

  function accountMenuItems() {
    const menu = document.getElementById("uiV4AccountMenu");
    if (!(menu instanceof HTMLElement) || menu.hidden) return [];
    return Array.from(menu.querySelectorAll("button:not(:disabled)"));
  }

  function focusAccountItem(index) {
    const items = accountMenuItems();
    if (!items.length) return;
    items[(index + items.length) % items.length]?.focus({ preventScroll: true });
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
    if (!document.body) return;
    decorateBusinessWorkspace();
    ensureSkipLink();
    ensureSidebarSemantics();
    ensureTopbarSemantics();
    ensureBaseInteractiveSemantics();
    decorateScrollableRegions();
    markTaskHierarchy();
    syncViewportMetrics();
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

    const accountToggle = event.target.closest?.("#uiV4AccountToggle");
    const accountMenu = document.getElementById("uiV4AccountMenu");
    if (accountToggle && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
      event.preventDefault();
      if (accountMenu?.hidden) accountToggle.click();
      requestAnimationFrame(() => focusAccountItem(event.key === "ArrowUp" ? -1 : 0));
      return;
    }

    if (accountMenu instanceof HTMLElement && !accountMenu.hidden && accountMenu.contains(event.target)) {
      const items = accountMenuItems();
      const current = items.indexOf(event.target.closest?.("button"));
      if (event.key === "ArrowDown") {
        event.preventDefault();
        focusAccountItem(current + 1);
        return;
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        focusAccountItem(current - 1);
        return;
      }
      if (event.key === "Home") {
        event.preventDefault();
        focusAccountItem(0);
        return;
      }
      if (event.key === "End") {
        event.preventDefault();
        focusAccountItem(-1);
        return;
      }
    }

    if (event.key === "Escape") {
      const accountWasOpen = accountMenu instanceof HTMLElement && !accountMenu.hidden;
      const sidebarWasOpen = document.body.classList.contains("ui-v4-sidebar-open");
      window.setTimeout(() => {
        if (accountWasOpen) document.getElementById("uiV4AccountToggle")?.focus({ preventScroll: true });
        if (sidebarWasOpen) document.getElementById("uiV4MobileMenu")?.focus({ preventScroll: true });
        ensureSidebarSemantics();
      }, 0);
    }

    if ((event.key === "Enter" || event.key === " ") && event.target.closest?.(PAGE_NAV_SELECTOR)) {
      keyboardNavigationPending = true;
    }
  }

  function handleClick(event) {
    if (event.detail === 0 && event.target.closest?.(PAGE_NAV_SELECTOR)) {
      keyboardNavigationPending = true;
      window.ZHILINK_UI_V4_RUNTIME?.schedule?.("keyboard-navigation");
    }

    const mobileButton = event.target.closest?.("#uiV4MobileMenu");
    const backdrop = event.target.closest?.("#uiV4MobileBackdrop");
    const sidebarNav = event.target.closest?.("#navList button[data-section]");
    const wasOpen = document.body.classList.contains("ui-v4-sidebar-open");

    if (mobileButton) {
      const opening = !wasOpen;
      requestAnimationFrame(() => {
        ensureSidebarSemantics();
        if (opening && document.body.classList.contains("ui-v4-sidebar-open")) {
          const active = document.querySelector("#navList button.active") || document.querySelector("#navList button[data-section]");
          active?.focus({ preventScroll: true });
        }
      });
      return;
    }

    if (backdrop && wasOpen) {
      window.setTimeout(() => {
        ensureSidebarSemantics();
        document.getElementById("uiV4MobileMenu")?.focus({ preventScroll: true });
      }, 0);
      return;
    }

    if (sidebarNav && wasOpen) requestAnimationFrame(ensureSidebarSemantics);
  }

  function scheduleViewportSync() {
    if (resizeFrame) cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(() => {
      resizeFrame = 0;
      syncViewportMetrics();
      ensureSidebarSemantics();
      decorateScrollableRegions();
    });
  }

  function start() {
    if (started) return;
    started = true;
    sync();
    window.ZHILINK_UI_V4_RUNTIME?.subscribe?.(sync, { immediate: false });
    document.addEventListener("keydown", handleKeydown, true);
    document.addEventListener("click", handleClick, true);
    document.addEventListener("pointerdown", () => document.body.classList.remove("ui-v4-keyboard-user"), true);
    window.addEventListener("resize", scheduleViewportSync, { passive: true });
    window.visualViewport?.addEventListener("resize", scheduleViewportSync, { passive: true });
    window.visualViewport?.addEventListener("scroll", scheduleViewportSync, { passive: true });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();