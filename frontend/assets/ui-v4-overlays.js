/* UI V4 overlays: one accessibility and interaction contract for dialogs and drawers. */
(() => {
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
      isOpen: () => document.body.classList.contains("ui-v4-api-open"),
      close: () => document.getElementById("uiV4ApiClose"),
      initial: () => document.getElementById("modelConfigAdvancedSettingsSummary") || document.getElementById("apiKey"),
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
    {
      key: "meeting-sources",
      container: () => document.getElementById("meetingSourceDialog"),
      dialog: () => document.querySelector("#meetingSourceDialog .meeting-source-dialog"),
      isOpen: () => document.getElementById("meetingSourceDialog")?.classList.contains("show") === true,
      close: () => document.querySelector("#meetingSourceDialog button[data-close-meeting-sources]"),
      initial: () => document.querySelector("#meetingSourceDialog button[data-close-meeting-sources]"),
    },
    {
      key: "policy-sources",
      container: () => document.getElementById("officialPolicyModal"),
      dialog: () => document.querySelector("#officialPolicyModal .policy-source-dialog"),
      isOpen: () => document.getElementById("officialPolicyModal")?.classList.contains("show") === true,
      close: () => document.querySelector("#officialPolicyModal [data-close-policy-sources]"),
      initial: () => document.querySelector("#officialPolicyModal [data-close-policy-sources]"),
    },
    {
      key: "structured",
      container: () => document.getElementById("structuredResultModal"),
      dialog: () => document.querySelector("#structuredResultModal .structured-dialog"),
      isOpen: () => document.getElementById("structuredResultModal")?.classList.contains("show") === true,
      close: () => document.querySelector("#structuredResultModal [data-close-structured]"),
      initial: () => document.querySelector("#structuredResultModal [data-close-structured]"),
    },
    {
      key: "review",
      container: () => document.getElementById("reviewWorkflowModal"),
      dialog: () => document.querySelector("#reviewWorkflowModal .review-dialog"),
      isOpen: () => document.getElementById("reviewWorkflowModal")?.classList.contains("show") === true,
      close: () => document.querySelector("#reviewWorkflowModal [data-close-review]"),
      initial: () => document.getElementById("reviewContentInput"),
    },
    {
      key: "service",
      container: () => document.getElementById("serviceWorkflowModal"),
      dialog: () => document.querySelector("#serviceWorkflowModal .service-workflow-dialog"),
      isOpen: () => document.getElementById("serviceWorkflowModal")?.classList.contains("show") === true,
      close: () => document.querySelector("#serviceWorkflowModal [data-sw-close]"),
      initial: () => document.getElementById("swFilter"),
    },
  ];

  const OPENER_SELECTOR = [
    "#openApiSettings", "#openAccountManager", "#openProjectManager", "#openKnowledgeBase", "#openIdentity", "#identityChip",
    "#uiV4ProjectContext", "#uiV4KnowledgeNav", "#uiV4SidebarAllProjects", "[data-ui-v4-account]",
    "[data-open-meeting-sources]", "#searchOfficialPolicy", "[data-open-policy-sources]", "[data-open-structured]", "[data-open-review]", "#openServiceWorkflow",
  ].join(",");

  let active = null;
  let returnFocus = null;
  let pendingOpener = null;

  function visible(element) {
    if (!(element instanceof HTMLElement)) return false;
    if (element.hidden || element.getAttribute("aria-hidden") === "true") return false;
    const style = window.getComputedStyle(element);
    if (style.display === "none" || style.visibility === "hidden") return false;
    return Boolean(element.offsetWidth || element.offsetHeight || element.getClientRects().length);
  }
  function focusables(dialog) { return dialog ? Array.from(dialog.querySelectorAll(FOCUSABLE)).filter(visible) : []; }
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
    if (document.activeElement instanceof Element && dialog.contains(document.activeElement)) return;
    const preferred = entry.initial();
    if (visible(preferred)) return preferred.focus({ preventScroll: true });
    const first = focusables(dialog)[0];
    if (first) first.focus({ preventScroll: true }); else dialog.focus({ preventScroll: true });
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
      if (target instanceof HTMLElement && target.isConnected && !target.disabled && visible(target)) target.focus({ preventScroll: true });
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
    const close = active?.close();
    if (close instanceof HTMLElement) close.click();
  }
  function trapFocus(event) {
    if (!active || event.key !== "Tab") return;
    const dialog = active.dialog();
    if (!dialog) return;
    const items = focusables(dialog);
    if (!items.length) { event.preventDefault(); dialog.focus({ preventScroll: true }); return; }
    const first = items[0];
    const last = items[items.length - 1];
    const current = document.activeElement;
    if (!dialog.contains(current)) { event.preventDefault(); (event.shiftKey ? last : first).focus({ preventScroll: true }); return; }
    if (event.shiftKey && current === first) { event.preventDefault(); last.focus({ preventScroll: true }); }
    else if (!event.shiftKey && current === last) { event.preventDefault(); first.focus({ preventScroll: true }); }
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
  function start() {
    document.addEventListener("click", event => {
      const opener = event.target.closest?.(OPENER_SELECTOR);
      if (opener instanceof HTMLElement && visible(opener)) pendingOpener = opener;
    }, true);
    document.addEventListener("keydown", handleKeydown, true);
    window.ZHILINK_UI_V4_RUNTIME?.subscribe?.(sync, { immediate: false });
    sync();
    window.ZHILINK_UI_V4_OVERLAYS_READY = true;
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true });
  else start();
})();
