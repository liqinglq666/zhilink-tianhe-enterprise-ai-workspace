/* UI V4 final QA: canonical responsive and accessibility presentation controller. */
(() => {
  const PAGE_NAV_SELECTOR = "#navList button[data-section], [data-goto]";
  const SCROLLABLE_SELECTOR = ".result-section-content, .structured-table-wrap";
  const MOBILE_BREAKPOINT = 1020;
  let keyboardNavigationPending = false;
  let started = false;
  let resizeFrame = 0;

  function setText(element, value) {
    if (element && element.textContent !== value) element.textContent = value;
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

  function refineCustomerCopy() {
    setText(document.querySelector('[data-ui-v4-account="api"]'), "AI 服务设置");
    setText(document.getElementById("openApiSettings"), "AI 服务设置");

    const pending = document.querySelector("#uiV4PendingList .ui-v4-panel-empty");
    if (pending && /没有识别到待确认事项|没有待确认事项/.test(pending.textContent || "")) {
      setText(pending, "当前没有待你确认的事项。新结果需要复核时会显示在这里。");
    }

    const recent = document.getElementById("recentMaterials");
    if (recent?.classList.contains("empty") && /没有最近材料|暂无.*材料|暂无.*结果/.test(recent.textContent || "")) {
      setText(recent, "还没有最近结果。完成一次业务任务后，这里会显示你的最新材料。");
    }

    const safetyTitle = document.querySelector("#home .ui-v4-safety-strip h3");
    if (safetyTitle && safetyTitle.textContent.trim() === "使用原则") setText(safetyTitle, "使用与复核");

    const usageLabel = document.querySelector("#uiV4UsagePanel .ui-v4-panel-head > span");
    if (usageLabel && /正式材料|已生成材料/.test(usageLabel.textContent || "")) setText(usageLabel, "工作概览");
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
    ensureSkipLink();
    ensureSidebarSemantics();
    ensureTopbarSemantics();
    ensureBaseInteractiveSemantics();
    decorateScrollableRegions();
    refineCustomerCopy();
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
