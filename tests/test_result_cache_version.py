from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "frontend" / "assets" / "data-provenance-guard.js"
POLICY = ROOT / "frontend" / "assets" / "policy-sources.js"


def test_result_cache_guard_is_single_asset_without_wrapper_loader():
    source = GUARD.read_text(encoding="utf-8")

    assert 'STYLE_URL = "/assets/data-provenance-guard.css?v=20260806.1"' in source
    assert 'link.dataset.zhilinkDataProvenance = "true"' in source
    assert "function ensureStyles()" in source
    assert "CORE_SCRIPT" not in source
    assert "loadCoreGuard" not in source
    assert not (ROOT / "frontend" / "assets" / "data-provenance-guard-v2.js").exists()


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
    assert "current.results = results" in source
    assert "window.showResult?.(key, {})" in source


def test_policy_schema_migration_is_owned_by_unified_guard_not_policy_ui():
    guard = GUARD.read_text(encoding="utf-8")
    policy = POLICY.read_text(encoding="utf-8")

    assert 'policy: "20260807-policy-grounded-v3"' in guard
    assert "quarantineLegacyResults" in guard
    assert "stampCommittedResult" in guard
    assert "POLICY_RESULT_SCHEMA_VERSION" not in policy
    assert "migrateStalePolicyResult" not in policy
    assert "stampPolicyResultVersion" not in policy
    assert 'sessionStorage.removeItem("zhilian_form_inputs")' not in guard


def test_module_schema_upgrades_do_not_invalidate_unrelated_current_results():
    source = GUARD.read_text(encoding="utf-8")

    assert 'return RESULT_SCHEMA_VERSIONS[key] || BASE_RESULT_SCHEMA_VERSION' in source
    assert 'contract: "20260807-contract-grounded-v3"' in source
    assert 'policy: "20260807-policy-grounded-v3"' in source
    assert 'meeting: "20260807-contract-grounded-v3"' not in source
    assert 'meeting: "20260807-policy-grounded-v3"' not in source
    assert "ZHILINK_RESULT_SCHEMA_VERSIONS" in source


def test_new_results_receive_module_schema_version_from_commit_event():
    source = GUARD.read_text(encoding="utf-8")

    assert 'window.addEventListener("zhilink:result-updated", event =>' in source
    assert 'event.detail?.source === "commit"' in source
    assert "stampCommittedResult(key)" in source
    assert "current.meta[key].result_schema_version = expectedVersion(key)" in source
    assert "persistMeta()" in source
    assert "zhilink:result-schema-stamped" in source
