from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "frontend" / "assets" / "data-provenance-guard-v2.js"
POLICY = ROOT / "frontend" / "assets" / "policy-sources.js"


def test_result_cache_guard_loads_its_core_assets_without_legacy_ui_loader():
    source = GUARD.read_text(encoding="utf-8")

    assert 'const CORE_SCRIPT = "/assets/data-provenance-guard.js?v=20260806.1"' in source
    assert 'const CORE_STYLE = "/assets/data-provenance-guard.css?v=20260806.1"' in source
    assert 'style.dataset.zhilinkDataProvenance = "true"' in source
    assert 'script.dataset.zhilinkDataProvenanceCore = "true"' in source
    assert "loadCoreGuard();" in source


def test_stale_generated_results_are_quarantined_before_reuse():
    source = GUARD.read_text(encoding="utf-8")

    assert 'const BASE_RESULT_SCHEMA_VERSION = "20260806-grounded-output-v2"' in source
    assert 'contract: "20260807-contract-grounded-v3"' in source
    assert 'policy: "20260807-policy-grounded-v3"' in source
    assert 'const QUARANTINE_STORAGE = "zhilian_legacy_result_quarantine_v1"' in source
    assert 'String(meta?.[key]?.result_schema_version || "") !== expectedVersion(key)' in source
    assert "expected_versions" in source
    assert "delete results[key]" in source
    assert "delete meta[key]" in source
    assert "persistActiveResults(results, meta)" in source
    assert "sessionStorage.removeItem(STRUCTURED_STORAGE)" in source
    assert "active.results = results" in source
    assert "window.showResult(key, {})" in source


def test_policy_bundle_has_independent_no_store_cache_migration():
    source = POLICY.read_text(encoding="utf-8")

    assert 'POLICY_RESULT_SCHEMA_VERSION = "20260807-policy-grounded-v3"' in source
    assert "migrateStalePolicyResult" in source
    assert "delete results.policy" in source
    assert "delete meta.policy" in source
    assert "stampPolicyResultVersion" in source
    assert 'if (key === "policy")' in source
    assert "政策需求输入已保留" in source
    assert 'sessionStorage.removeItem("zhilian_form_inputs")' not in source
    assert 'sessionStorage.removeItem("policyDemand")' not in source


def test_module_schema_upgrades_do_not_invalidate_unrelated_current_results():
    source = GUARD.read_text(encoding="utf-8")

    assert 'return RESULT_SCHEMA_VERSIONS[key] || BASE_RESULT_SCHEMA_VERSION' in source
    assert 'contract: "20260807-contract-grounded-v3"' in source
    assert 'policy: "20260807-policy-grounded-v3"' in source
    assert 'meeting: "20260807-contract-grounded-v3"' not in source
    assert 'meeting: "20260807-policy-grounded-v3"' not in source
    assert "ZHILINK_RESULT_SCHEMA_VERSIONS" in source


def test_new_results_receive_module_schema_version_without_clearing_inputs():
    source = GUARD.read_text(encoding="utf-8")

    original_call = source.index("const value = original.apply(this, arguments)")
    stamp_call = source.index("stampCurrentResult(key)", original_call)
    assert original_call < stamp_call
    assert "active.meta[key].result_schema_version = expectedVersion(key)" in source
    assert 'sessionStorage.setItem(META_STORAGE, JSON.stringify(active.meta))' in source
    assert "zhilian_form_inputs" not in source
    assert "meetingInput" not in source
    assert "policyDemand" not in source
