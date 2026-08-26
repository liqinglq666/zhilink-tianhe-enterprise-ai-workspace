from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_overlay_controller_covers_all_workspace_dialogs() -> None:
    script = (ASSETS / "ui-v4-overlays.js").read_text(encoding="utf-8")

    for key in ("api", "account", "project", "knowledge", "identity", "meeting-sources", "policy-sources", "structured", "review", "service"):
        assert f'key: "{key}"' in script

    assert 'document.getElementById("meetingSourceDialog")' in script
    assert '#meetingSourceDialog .meeting-source-dialog' in script
    assert '[data-open-meeting-sources]' in script
    assert 'button[data-close-meeting-sources]' in script
    assert 'document.getElementById("officialPolicyModal")' in script
    assert '#officialPolicyModal .policy-source-dialog' in script
    assert '#searchOfficialPolicy' in script
    assert '[data-open-policy-sources]' in script
    assert '[data-close-policy-sources]' in script
    assert 'document.getElementById("uiV4ApiClose")' in script
    assert 'document.getElementById("modelConfigAdvancedSettingsSummary") || document.getElementById("apiKey")' in script
    assert '[data-ui-v4-account]' in script
    assert 'dialog.setAttribute("aria-modal", "true")' in script
    assert 'dialog.setAttribute("tabindex", "-1")' in script
    assert 'shell.inert = true' in script
    assert 'shell.inert = false' in script
    assert 'event.key === "Escape"' in script
    assert 'event.key !== "Tab"' in script
    assert 'last.focus({ preventScroll: true })' in script
    assert 'first.focus({ preventScroll: true })' in script
    assert 'target.focus({ preventScroll: true })' in script
    assert 'opener instanceof HTMLElement && visible(opener)' in script
    assert 'window.ZHILINK_UI_V4_RUNTIME?.subscribe?.(sync, { immediate: false })' in script
    assert script.count("OVERLAYS.forEach(decorate);") == 1
    assert "MutationObserver" not in script
    assert 'window.ZHILINK_UI_V4_OVERLAYS_READY = true' in script


def test_overlay_dom_changes_delegate_scheduling_to_shared_runtime() -> None:
    policy = (ASSETS / "policy-sources.js").read_text(encoding="utf-8")
    drawer = (ASSETS / "api-drawer-v4.js").read_text(encoding="utf-8")
    runtime = (ASSETS / "ui-v4-runtime.js").read_text(encoding="utf-8")
    overlays = (ASSETS / "ui-v4-overlays.js").read_text(encoding="utf-8")

    assert 'window.ZHILINK_UI_V4_RUNTIME?.schedule?.("policy-sources-open")' not in policy
    assert 'window.ZHILINK_UI_V4_RUNTIME?.schedule?.("policy-sources-close")' not in policy
    assert 'window.ZHILINK_UI_V4_RUNTIME?.schedule?.("api-open")' not in drawer
    assert 'window.ZHILINK_UI_V4_RUNTIME?.schedule?.("api-close")' not in drawer
    assert 'attributeFilter: ["class", "hidden", "aria-hidden", "aria-expanded", "disabled"]' in runtime
    assert 'event.key === "Escape"' not in policy
    assert 'key: "policy-sources"' in overlays
    assert '#officialPolicyModal .policy-source-dialog' in overlays
    assert '[data-close-policy-sources]' in overlays


def test_overlay_controller_owns_business_dialog_keyboard_and_initial_focus() -> None:
    app = (ASSETS / "app.js").read_text(encoding="utf-8")
    meeting = (ASSETS / "meeting-user-view.js").read_text(encoding="utf-8")
    structured = (ASSETS / "structured-results.js").read_text(encoding="utf-8")
    review = (ASSETS / "review-workflow.js").read_text(encoding="utf-8")
    overlays = (ASSETS / "ui-v4-overlays.js").read_text(encoding="utf-8")

    assert 'event.key === "Escape"' not in meeting
    assert 'event.key === "Escape"' not in structured
    assert 'event.key === "Escape"' not in review
    assert 'setTimeout(() => document.getElementById("reviewContentInput")?.focus(), 30)' not in review
    assert 'document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeIdentityModal(); });' not in app
    assert 'setTimeout(() => $("identityOrg")?.focus(), 30);' not in app

    assert 'key: "identity"' in overlays
    assert 'close: () => document.getElementById("closeIdentity")' in overlays
    assert 'initial: () => document.getElementById("identityOrg")' in overlays
    assert 'key: "meeting-sources"' in overlays
    assert 'close: () => document.querySelector("#meetingSourceDialog button[data-close-meeting-sources]")' in overlays
    assert 'key: "structured"' in overlays
    assert 'close: () => document.querySelector("#structuredResultModal [data-close-structured]")' in overlays
    assert 'key: "review"' in overlays
    assert 'close: () => document.querySelector("#reviewWorkflowModal [data-close-review]")' in overlays
    assert 'initial: () => document.getElementById("reviewContentInput")' in overlays


def test_overlay_controller_does_not_own_business_or_persistence_logic() -> None:
    script = (ASSETS / "ui-v4-overlays.js").read_text(encoding="utf-8")

    for forbidden in (
        "fetch(", "state.results", "setResult", "saveConfig", "sessionStorage", "localStorage", "/api/", "liveApiClose", "liveAccount",
    ):
        assert forbidden not in script


def test_overlay_styles_unify_desktop_and_mobile_surfaces() -> None:
    stylesheet = (ASSETS / "ui-v4-overlays.css").read_text(encoding="utf-8")

    assert "body.ui-v4-overlay-active" in stylesheet
    assert '[data-ui-v4-overlay-active="true"]' in stylesheet
    assert "#accountManagerModal .account-dialog-header" in stylesheet
    assert "#projectManagerModal .project-dialog-header" in stylesheet
    assert "#knowledgeBaseModal .knowledge-dialog-header" in stylesheet
    assert '#identityModal .modal-card[data-ui-v4-dialog="identity"] .modal-head' in stylesheet
    assert '#meetingSourceDialog .meeting-source-dialog[data-ui-v4-dialog="meeting-sources"]' in stylesheet
    assert ".meeting-source-backdrop" in stylesheet
    assert '#apiPanel[data-ui-v4-dialog="api"]' in stylesheet
    assert "#uiV4ApiBackdrop" in stylesheet
    assert "100dvh" in stylesheet
    assert "env(safe-area-inset-top)" in stylesheet
    assert "env(safe-area-inset-bottom)" in stylesheet
    assert "@media (prefers-reduced-motion: reduce)" in stylesheet
    assert "live-api-" not in stylesheet
