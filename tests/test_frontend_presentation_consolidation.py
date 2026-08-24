from pathlib import Path

from backend.project_routes import UI_SCRIPTS

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"


def test_workspace_presentation_is_owned_by_final_qa() -> None:
    final_qa = (ASSETS / "ui-v4-final-qa.js").read_text(encoding="utf-8")

    assert not (ASSETS / "ui-v4-workspace.js").exists()
    assert "ui-v4-workspace.js" not in UI_SCRIPTS
    assert "function decorateBusinessWorkspace()" in final_qa
    assert 'document.documentElement.dataset.zhilinkWorkspace = "v4"' in final_qa
    assert 'textarea.setAttribute("spellcheck", "false")' in final_qa
    assert 'button.insertAdjacentHTML("beforeend", ICONS.arrow)' in final_qa
    assert 'meta.className = "ui-v4-module-meta"' in final_qa
