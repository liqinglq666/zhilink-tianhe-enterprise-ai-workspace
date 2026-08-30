from pathlib import Path

from backend.project_routes import UI_SCRIPTS


ROOT = Path(__file__).resolve().parents[1]
DELETE_MODULE = ROOT / "frontend" / "assets" / "result-delete.js"


def test_result_delete_module_is_bundled_after_result_presentation():
    assert "result-delete.js" in UI_SCRIPTS
    assert UI_SCRIPTS.index("result-delete.js") > UI_SCRIPTS.index("ui-v4-results.js")


def test_result_delete_clears_only_current_result_and_persists_state():
    source = DELETE_MODULE.read_text(encoding="utf-8")
    assert "delete state.results[normalizedKey]" in source
    assert "delete state.meta[normalizedKey]" in source
    assert 'sessionStorage.setItem("zhilian_results"' in source
    assert 'sessionStorage.setItem("zhilian_meta"' in source
    assert 'showResult(normalizedKey, {}, "commit")' in source
    assert "updateProgress()" in source


def test_result_delete_requires_confirmation_and_preserves_inputs():
    source = DELETE_MODULE.read_text(encoding="utf-8")
    assert "window.confirm" in source
    assert "不会清空该模块的输入内容" in source
    assert "formInputIds" not in source
    assert "zhilian_form_inputs" not in source
