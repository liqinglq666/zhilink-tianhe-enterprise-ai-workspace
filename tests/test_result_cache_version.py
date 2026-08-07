from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOADER = ROOT / "frontend" / "assets" / "ui-redesign-live-fixes.js"
GUARD = ROOT / "frontend" / "assets" / "data-provenance-guard-v2.js"


def test_live_loader_uses_versioned_result_cache_guard():
    source = LOADER.read_text(encoding="utf-8")

    assert "/assets/data-provenance-guard-v2.js?v=20260806.2" in source
    assert "script.dataset.zhilinkDataProvenance = \"true\"" in source


def test_stale_generated_results_are_quarantined_before_reuse():
    source = GUARD.read_text(encoding="utf-8")

    assert 'const RESULT_SCHEMA_VERSION = "20260806-grounded-output-v2"' in source
    assert 'const QUARANTINE_STORAGE = "zhilian_legacy_result_quarantine_v1"' in source
    assert 'String(meta?.[key]?.result_schema_version || "") !== RESULT_SCHEMA_VERSION' in source
    assert "delete results[key]" in source
    assert "delete meta[key]" in source
    assert "persistActiveResults(results, meta)" in source
    assert "sessionStorage.removeItem(STRUCTURED_STORAGE)" in source
    assert "active.results = results" in source
    assert "window.showResult(key, {})" in source


def test_new_results_receive_current_schema_version_without_clearing_inputs():
    source = GUARD.read_text(encoding="utf-8")

    original_call = source.index("const value = original.apply(this, arguments)")
    stamp_call = source.index("stampCurrentResult(key)", original_call)
    assert original_call < stamp_call
    assert "active.meta[key].result_schema_version = RESULT_SCHEMA_VERSION" in source
    assert 'sessionStorage.setItem(META_STORAGE, JSON.stringify(active.meta))' in source
    assert "zhilian_form_inputs" not in source
    assert "meetingInput" not in source
