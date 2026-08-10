from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_overlay_controller_covers_all_workspace_dialogs() -> None:
    script = (ASSETS / "ui-v4-overlays.js").read_text(encoding="utf-8")

    for key in ("api", "account", "project", "knowledge", "identity"):
        assert f'key: "{key}"' in script

    assert 'dialog.setAttribute("aria-modal", "true")' in script
    assert 'dialog.setAttribute("tabindex", "-1")' in script
    assert 'shell.inert = true' in script
    assert 'shell.inert = false' in script
    assert 'event.key === "Escape"' in script
    assert 'event.key !== "Tab"' in script
    assert 'last.focus({ preventScroll: true })' in script
    assert 'first.focus({ preventScroll: true })' in script
    assert 'target.focus({ preventScroll: true })' in script
    assert 'window.ZHILINK_UI_V4_OVERLAYS_READY = true' in script


def test_overlay_controller_does_not_own_business_or_persistence_logic() -> None:
    script = (ASSETS / "ui-v4-overlays.js").read_text(encoding="utf-8")

    for forbidden in (
        "fetch(",
        "state.results",
        "setResult",
        "saveConfig",
        "sessionStorage",
        "localStorage",
        "/api/",
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
    assert '#apiPanel[data-ui-v4-dialog="api"]' in stylesheet
    assert "100dvh" in stylesheet
    assert "env(safe-area-inset-bottom)" in stylesheet
    assert "@media (prefers-reduced-motion: reduce)" in stylesheet
