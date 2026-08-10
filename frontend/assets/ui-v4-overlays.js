/* UI V4 overlays: one accessibility and interaction contract for dialogs and drawers. */
(() => {
  const VERSION = "20260810.1";
  const FOCUSABLE = [
    "a[href]",
    "button:not([disabled])",
    "input:not([disabled]):not([type='hidden'])",
    "select:not([disabled])",
    "textarea:not([disabled])",
    "[tabindex]:not([tabindex='-1'])",
    "[contenteditable='true']",
  ].join(",");

  const OVERLAYS = [
    {
      key: "api",
      container: () => document.getElementById("apiPanel"),
      dialog: () => document.getElementById("apiPanel"),
      isOpen: () => document.body.classList.contains("live-api-open"),
      close: () => document.getElementById("liveApiClose"),
      initial: () => document.getElementById("apiKey"),
    },
    {
      key: "account",
      container: () => document.getElementById("accountManagerModal"),
      dialog: () => document.querySelector("#accountManagerModal .account-dialog"),
      isOpen: () => document.getElementById("accountManagerModal")?.classList.contains("show") === true,
      close: () => document.querySelector("#accountManagerModal button[data-close-account-manager]"),
      initial: () => document.querySelector("#accountManagerModal input:not([type='hidden']), #accountManagerModal select"),
    },
    {
      key: "project",
      container: () => document.getElementById("projectManagerModal"),
      dialog: () => document.querySelector("#projectManagerModal .project-dialog"),
      isOpen: () => document.getElementById("projectManagerModal")?.classList.contains("show") === true,
      close: () => document.querySelector("#projectManagerModal button[data-close-project-manager]"),
      initial: () => document.getElementById("projectNameInput"),
    },
    {
      key: "knowledge",
      container: () => document.getElementById("knowledgeBaseModal"),
      dialog: () => document.querySelector("#knowledgeBaseModal .knowledge-dialog"),
      isOpen: () => document.getElementById("knowledgeBaseModal")?.classList.contains("show") === true,
      close: () => document.querySelector("#knowledgeBaseModal button[data-close-knowledge]"),
      initial: () => document.getElementById("knowledgeSearchQuery"),
    },
    {
      key: "identity",
      container: () => document.getElementById("identityModal"),
      dialog: () => document.querySelector("#identityModal .modal-card"),
      isOpen: () => document.getElementById("identityModal")?.classList.contains("show") === true,
      close: () => document.getElementById("closeIdentity"),
      initial: () => document.getElementById("identityOrg"),
    },
  ];

  const OPENER_SELECTOR = [
    "#openApiSettings",
    "#openAccountManager",
    "#openProjectManager",
    "#openKnowledgeBase",
    "#openIdentity",
    "#identityChip",
    "#uiV4ProjectContext",
    "#uiV4KnowledgeNav",
    "#liveSidebarAllProjects",
    "[data-live-account='account']",
    "[data-live-account='identity']",
    "[data-live-account='api']",
  ].join(",");

  let active = null;
  let returnFocus = null;
  let pendingOpener = null;
  let observer = null;
  let queued = false;

  function ensureStyles() {
    if (document.querySelector("link[data-ui-v4-overlays]")) return;
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `/assets/ui-v4-overlays.css?v=${VERSION}`;
    link.dataset.uiV4Overlays = "true";
    document.head.appendChild(link);
  }

  function visible(element) {
    if (!(element instanceof HTMLElement)) return false;
    if (element.hidden || element.getAttribute("aria-hidden") === "true") return false;
    const style = window.getComputedStyle(element);
    if (style.display === "none" || style.visibility === "hidden") return false;
    return Boolean(element.offsetWidth || element.offsetHeight || element.getClientRects().length);
  }

  function focusables(dialog) {
    if (!dialog) return [];
    return Array.from(dialog.querySelectorAll(FOCUSABLE)).filter(visible);
  }

  function decorate(entry) {
    const container = entry.container();
    const dialog = entry.dialog();
    if (!container || !dialog) return;
    container.dataset.uiV4Overlay = entry.key;
    dialog.dataset.uiV4Dialog = entry.key;
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    if (!dialog.hasAttribute("tabindex")) dialog.setAttribute("tabindex", "-1");
  }

  function setWorkspaceInert(inert) {
    const shell = document.querySelector(".shell");
    if (!shell) return;
    if (inert) {
      shell.inert = true;
      shell.dataset.uiV4OverlayInert = "true";
    } else if (shell.dataset.uiV4OverlayInert === "true") {
      shell.inert = false;
      delete shell.dataset.uiV4OverlayInert;
    }
  }

  function findOpenOverlay() {
    if (active?.isOpen()) return active;
    return OVERLAYS.find(entry => entry.isOpen() && entry.container() && entry.dialog()) || null;
  }

  function focusInside(entry) {
    const dialog = entry?.dialog();
    if (!dialog) return;
    const current = document.activeElement;
    if (current instanceof Element && dialog.contains(current)) return;
    const preferred = entry.initial();
    if (visible(preferred)) {
      preferred.focus({ preventScroll: true });
      return;
    }
    const first = focusables(dialog)[0];
    if (first) first.focus({ preventScroll: true });
    else dialog.focus({ preventScroll: true });
  }

  function activate(entry) {
    active = entry;
    const container = entry.container();
    const dialog = entry.dialog();
    if (!container || !dialog) return;

    returnFocus = pendingOpener && visible(pendingOpener)
      ? pendingOpener
      : (document.activeElement instanceof HTMLElement && !dialog.contains(document.activeElement) ? document.activeElement : null);
    pendingOpener = null;

    document.body.classList.add("ui-v4-overlay-active");
    document.body.dataset.uiV4Overlay = entry.key;
    container.dataset.uiV4OverlayActive = "true";
    container.setAttribute("aria-hidden", "false");
    setWorkspaceInert(true);

    window.setTimeout(() => focusInside(entry), 60);
  }

  function deactivate(previous) {
    const container = previous?.container();
    if (container) delete container.dataset.uiV4OverlayActive;
    document.body.classList.remove("ui-v4-overlay-active");
    delete document.body.dataset.uiV4Overlay;
    setWorkspaceInert(false);

    const target = returnFocus;
    returnFocus = null;
    active = null;
    window.setTimeout(() => {
      if (target instanceof HTMLElement && target.isConnected && !target.disabled && visible(target)) {
        target.focus({ preventScroll: true });
      }
    }, 0);
  }

  function sync() {
    OVERLAYS.forEach(decorate);
    const next = findOpenOverlay();
    if (next === active) return;
    if (active) deactivate(active);
    if (next) activate(next);
  }

  function requestClose() {
    if (!active) return;
    const close = active.close();
    if (close instanceof HTMLElement) {
      close.click();
      return;
    }
    console.warn(`Overlay ${active.key} has no close control.`);
  }

  function trapFocus(event) {
    if (!active || event.key !== "Tab") return;
    const dialog = active.dialog();
    if (!dialog) return;
    const items = focusables(dialog);
    if (!items.length) {
      event.preventDefault();
      dialog.focus({ preventScroll: true });
      return;
    }

    const first = items[0];
    const last = items[items.length - 1];
    const current = document.activeElement;
    if (!dialog.contains(current)) {
      event.preventDefault();
      (event.shiftKey ? last : first).focus({ preventScroll: true });
      return;
    }
    if (event.shiftKey && current === first) {
      event.preventDefault();
      last.focus({ preventScroll: true });
    } else if (!event.shiftKey && current === last) {
      event.preventDefault();
      first.focus({ preventScroll: true });
    }
  }

  function handleKeydown(event) {
    if (!active) return;
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopImmediatePropagation();
      requestClose();
      return;
    }
    trapFocus(event);
  }

  function queueSync() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => {
      queued = false;
      sync();
    });
  }

  function installObserver() {
    if (observer || !document.body) return;
    observer = new MutationObserver(mutations => {
      const relevant = mutations.some(mutation => {
        if (mutation.type === "childList") return mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0;
        return mutation.type === "attributes" && ["class", "aria-hidden"].includes(mutation.attributeName);
      });
      if (relevant) queueSync();
    });
    observer.observe(document.body, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ["class", "aria-hidden"],
    });
  }

  function start() {
    ensureStyles();
    OVERLAYS.forEach(decorate);
    document.addEventListener("click", event => {
      const opener = event.target.closest?.(OPENER_SELECTOR);
      if (opener instanceof HTMLElement) pendingOpener = opener;
    }, true);
    document.addEventListener("keydown", handleKeydown, true);
    installObserver();
    sync();
    window.ZHILINK_UI_V4_OVERLAYS_READY = true;
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
