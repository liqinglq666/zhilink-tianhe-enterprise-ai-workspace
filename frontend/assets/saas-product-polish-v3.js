/* SaaS product polish v3 + release polish v4: presentation-only hierarchy and responsive semantics. */
(() => {
  const STYLE_URL = "/assets/saas-product-polish-v3.css?v=20260824.1";
  const RELEASE_STYLE_URL = "/assets/release-polish-v4.css?v=20260824.1";
  const runtime = window.ZHILINK_UI_V4_RUNTIME;
  const MOBILE_BREAKPOINT = 1020;
  let started = false;
  let resizeFrame = 0;

  function ensureStyle(href, marker) {
    if (document.querySelector(`link[${marker}]`)) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = href;
    link.setAttribute(marker, "true");
    document.head.appendChild(link);
  }

  function ensureStyles() {
    ensureStyle(STYLE_URL, "data-saas-product-polish-v3");
    ensureStyle(RELEASE_STYLE_URL, "data-release-polish-v4");
  }

  function setText(element, value) {
    if (element && element.textContent !== value) element.textContent = value;
  }

  function markTaskHierarchy() {
    document.querySelectorAll("#home .module-card[data-tool-key]").forEach(card => {
      card.dataset.productTier = card.classList.contains("ui-v4-secondary-task") ? "utility" : "primary";
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

  function syncNavigationSemantics() {
    document.querySelectorAll("#navList button[data-section]").forEach(button => {
      if (button.classList.contains("active")) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
  }

  function syncActionSemantics() {
    document.querySelectorAll(".sticky-actions, .ui-v4-form-actions").forEach(actions => {
      if (!actions.getAttribute("aria-label")) actions.setAttribute("aria-label", "当前页面操作");
    });
    const project = document.getElementById("uiV4ProjectContext");
    if (project && !project.getAttribute("aria-label")) project.setAttribute("aria-label", "打开当前项目与版本");
  }

  function syncViewportMetrics() {
    const visualHeight = Math.round(window.visualViewport?.height || window.innerHeight || 0);
    const visualWidth = Math.round(window.visualViewport?.width || window.innerWidth || 0);
    if (visualHeight > 0) document.documentElement.style.setProperty("--ui4-visual-height", `${visualHeight}px`);
    if (visualWidth > 0) document.documentElement.style.setProperty("--ui4-visual-width", `${visualWidth}px`);
    document.documentElement.dataset.uiV4Height = visualHeight <= 700 ? "short" : visualHeight <= 820 ? "compact" : "regular";
  }

  function syncAccountMenuSemantics() {
    const toggle = document.getElementById("uiV4AccountToggle");
    const menu = document.getElementById("uiV4AccountMenu");
    if (!(toggle instanceof HTMLButtonElement) || !(menu instanceof HTMLElement)) return;
    toggle.setAttribute("aria-haspopup", "menu");
    menu.setAttribute("role", "menu");
    menu.querySelectorAll("button").forEach(button => button.setAttribute("role", "menuitem"));
  }

  function syncMobileSidebarSemantics() {
    const sidebar = document.getElementById("primarySidebar") || document.querySelector(".sidebar");
    if (!(sidebar instanceof HTMLElement)) return;
    const mobile = window.innerWidth <= MOBILE_BREAKPOINT;
    if (!mobile) {
      sidebar.removeAttribute("aria-hidden");
      return;
    }
    sidebar.setAttribute("aria-hidden", document.body.classList.contains("ui-v4-sidebar-open") ? "false" : "true");
  }

  function accountMenuItems() {
    const menu = document.getElementById("uiV4AccountMenu");
    if (!(menu instanceof HTMLElement) || menu.hidden) return [];
    return Array.from(menu.querySelectorAll("button:not(:disabled)"));
  }

  function focusAccountItem(index) {
    const items = accountMenuItems();
    if (!items.length) return;
    const normalized = (index + items.length) % items.length;
    items[normalized]?.focus({ preventScroll: true });
  }

  function handleReleaseKeydown(event) {
    const toggle = event.target.closest?.("#uiV4AccountToggle");
    const menu = document.getElementById("uiV4AccountMenu");

    if (toggle && (event.key === "ArrowDown" || event.key === "ArrowUp")) {
      event.preventDefault();
      if (menu?.hidden) toggle.click();
      requestAnimationFrame(() => focusAccountItem(event.key === "ArrowUp" ? -1 : 0));
      return;
    }

    if (menu instanceof HTMLElement && !menu.hidden && menu.contains(event.target)) {
      const items = accountMenuItems();
      const current = items.indexOf(event.target.closest?.("button"));
      if (event.key === "ArrowDown") {
        event.preventDefault();
        focusAccountItem(current + 1);
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        focusAccountItem(current - 1);
      } else if (event.key === "Home") {
        event.preventDefault();
        focusAccountItem(0);
      } else if (event.key === "End") {
        event.preventDefault();
        focusAccountItem(-1);
      }
    }

    if (event.key === "Escape") {
      const accountWasOpen = menu instanceof HTMLElement && !menu.hidden;
      const sidebarWasOpen = document.body.classList.contains("ui-v4-sidebar-open");
      window.setTimeout(() => {
        if (accountWasOpen) document.getElementById("uiV4AccountToggle")?.focus({ preventScroll: true });
        if (sidebarWasOpen) document.getElementById("uiV4MobileMenu")?.focus({ preventScroll: true });
        syncMobileSidebarSemantics();
      }, 0);
    }
  }

  function handleReleaseClick(event) {
    const mobileButton = event.target.closest?.("#uiV4MobileMenu");
    const backdrop = event.target.closest?.("#uiV4MobileBackdrop");
    const sidebarNav = event.target.closest?.("#navList button[data-section]");
    const wasOpen = document.body.classList.contains("ui-v4-sidebar-open");

    if (mobileButton) {
      const opening = !wasOpen;
      requestAnimationFrame(() => {
        syncMobileSidebarSemantics();
        if (opening && document.body.classList.contains("ui-v4-sidebar-open")) {
          const active = document.querySelector("#navList button.active") || document.querySelector("#navList button[data-section]");
          active?.focus({ preventScroll: true });
        }
      });
      return;
    }

    if (backdrop && wasOpen) {
      window.setTimeout(() => {
        syncMobileSidebarSemantics();
        document.getElementById("uiV4MobileMenu")?.focus({ preventScroll: true });
      }, 0);
      return;
    }

    if (sidebarNav && wasOpen) requestAnimationFrame(syncMobileSidebarSemantics);
  }

  function scheduleViewportSync() {
    if (resizeFrame) cancelAnimationFrame(resizeFrame);
    resizeFrame = requestAnimationFrame(() => {
      resizeFrame = 0;
      syncViewportMetrics();
      syncMobileSidebarSemantics();
    });
  }

  function apply() {
    if (!document.body) return;
    ensureStyles();
    document.body.classList.add("ui-v4-saas-polish");
    document.body.classList.add("ui-v4-release-polish");
    document.documentElement.dataset.zhilinkProductPolish = "v3";
    document.documentElement.dataset.zhilinkReleasePolish = "v4";
    markTaskHierarchy();
    refineCustomerCopy();
    syncNavigationSemantics();
    syncActionSemantics();
    syncAccountMenuSemantics();
    syncViewportMetrics();
    syncMobileSidebarSemantics();
    window.ZHILINK_SAAS_PRODUCT_POLISH_V3_READY = true;
    window.ZHILINK_RELEASE_POLISH_V4_READY = true;
  }

  function start() {
    if (started) return;
    started = true;
    apply();
    runtime?.subscribe?.(apply, { immediate: false });
    document.addEventListener("keydown", handleReleaseKeydown, true);
    document.addEventListener("click", handleReleaseClick, true);
    window.addEventListener("resize", scheduleViewportSync, { passive: true });
    window.visualViewport?.addEventListener("resize", scheduleViewportSync, { passive: true });
    window.visualViewport?.addEventListener("scroll", scheduleViewportSync, { passive: true });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
