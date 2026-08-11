from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "frontend" / "assets"
RUNTIME = ASSETS / "ui-v4-runtime.js"


def test_runtime_is_the_single_shared_contract_registry() -> None:
    runtime = RUNTIME.read_text(encoding="utf-8")

    assert "window.ZHILINK_WORKSPACE_CONTRACTS = contracts" in runtime
    assert "window.ZHILINK_WORKSPACE_CONTRACTS_READY = true" in runtime
    assert 'typeof resultKeys !== "undefined" ? Array.from(resultKeys) : []' in runtime
    assert 'typeof resultTitles !== "undefined" ? { ...resultTitles } : {}' in runtime

    for marker in (
        'workspaceKey: "zhilian_workspace_key_v1"',
        'currentProject: "zhilian_current_project_v1"',
        'restoreSection: "zhilian_restore_section_v1"',
        'identity: "zhilian_identity"',
        'profile: "zhilian_profile"',
        'formInputs: "zhilian_form_inputs"',
        'results: "zhilian_results"',
        'meta: "zhilian_meta"',
        'structuredResults: "zhilian_structured_results_v1"',
        'exampleContexts: "zhilian_example_contexts_v1"',
        'legacyQuarantine: "zhilian_legacy_result_quarantine_v1"',
        'accountReady: "zhilink:account-ready"',
        'workspaceStateChange: "zhilink:workspace-state-change"',
        'projectChanged: "zhilink:project-changed"',
        'dataProvenanceReady: "zhilink:data-provenance-ready"',
        'resultSchemaStamped: "zhilink:result-schema-stamped"',
        'modelModeChange: "zhilink:model-mode-change"',
        'resultUpdated: "zhilink:result-updated"',
        'progressUpdated: "zhilink:progress-updated"',
        'structuredUpdated: "zhilink:structured-updated"',
        'reviewUpdated: "zhilink:review-updated"',
    ):
        assert marker in runtime


def test_contract_consumers_do_not_redeclare_shared_storage_or_event_literals() -> None:
    consumers = (
        "example-loader.js",
        "project-storage.js",
        "project-result-meta.js",
        "data-provenance-guard.js",
        "ui-v4-shell.js",
        "ui-v4-dashboard.js",
        "policy-sources.js",
        "meeting-user-view.js",
        "review-workflow.js",
        "structured-results.js",
    )
    forbidden_literals = (
        '"zhilian_workspace_key_v1"',
        '"zhilian_current_project_v1"',
        '"zhilian_restore_section_v1"',
        '"zhilian_example_contexts_v1"',
        '"zhilian_structured_results_v1"',
        '"zhilian_legacy_result_quarantine_v1"',
        '"zhilian_results"',
        '"zhilian_meta"',
        '"zhilink:account-ready"',
        '"zhilink:workspace-state-change"',
        '"zhilink:project-changed"',
        '"zhilink:data-provenance-ready"',
        '"zhilink:result-schema-stamped"',
        '"zhilink:result-updated"',
        '"zhilink:progress-updated"',
        '"zhilink:structured-updated"',
        '"zhilink:review-updated"',
    )

    for filename in consumers:
        source = (ASSETS / filename).read_text(encoding="utf-8")
        assert "window.ZHILINK_WORKSPACE_CONTRACTS" in source, filename
        for literal in forbidden_literals:
            assert literal not in source, f"{literal} redeclared in {filename}"


def test_project_storage_uses_result_event_instead_of_monkey_patching_set_result() -> None:
    source = (ASSETS / "project-storage.js").read_text(encoding="utf-8")

    assert "window.addEventListener(contracts.events.resultUpdated" in source
    assert 'event.detail?.source === "commit"' in source
    assert "const originalSetResult = setResult" not in source
    assert "setResult = function setResultAndMarkProject" not in source


def test_shell_and_provenance_share_core_result_catalogue() -> None:
    shell = (ASSETS / "ui-v4-shell.js").read_text(encoding="utf-8")
    provenance = (ASSETS / "data-provenance-guard.js").read_text(encoding="utf-8")

    assert "const RESULT_KEYS = contracts.resultKeys" in shell
    assert "const RESULT_TITLES = contracts.resultTitles" in shell
    assert "const BUSINESS_KEYS = contracts.resultKeys" in provenance
    assert "const SCHEMA_KEYS = contracts.schemaResultKeys" in provenance
    assert "const RESULT_TITLES = contracts.resultTitles" in provenance


def test_project_list_refresh_is_event_driven_without_background_polling() -> None:
    runtime = RUNTIME.read_text(encoding="utf-8")
    shell = (ASSETS / "ui-v4-shell.js").read_text(encoding="utf-8")

    assert "PROJECT_REFRESH_MS" not in shell
    assert "projectTimer" not in shell
    assert "window.setInterval(fetchProjects" not in shell
    assert "const PROJECT_CHANGED_EVENT = contracts.events.projectChanged" in shell
    assert "window.addEventListener(PROJECT_CHANGED_EVENT, fetchProjects)" in shell
    assert "response.ok && isProjectWrite(finalInput, finalInit)" in runtime
    assert "emitWindowEvent(events.projectChanged" in runtime
    assert "events.projectChanged" in runtime


def test_review_structured_policy_and_meeting_share_event_contracts() -> None:
    review = (ASSETS / "review-workflow.js").read_text(encoding="utf-8")
    structured = (ASSETS / "structured-results.js").read_text(encoding="utf-8")
    policy = (ASSETS / "policy-sources.js").read_text(encoding="utf-8")
    meeting = (ASSETS / "meeting-user-view.js").read_text(encoding="utf-8")

    assert "new CustomEvent(contracts.events.reviewUpdated" in review
    assert "window.addEventListener(contracts.events.resultUpdated" in review
    assert "new CustomEvent(contracts.events.structuredUpdated" in structured
    assert "window.addEventListener(contracts.events.resultUpdated" in structured
    for source in (policy, meeting):
        assert "contracts.events.resultUpdated" in source
        assert "contracts.events.structuredUpdated" in source
        assert "contracts.events.reviewUpdated" in source
