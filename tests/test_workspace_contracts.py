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


def test_runtime_owns_only_behavior_generic_v4_helpers() -> None:
    runtime = RUNTIME.read_text(encoding="utf-8")

    for marker in (
        "function readJson(raw, fallback)",
        "function setText(element, value)",
        "function escapeHtml(value)",
        "window.ZHILINK_UI_V4_HELPERS = Object.freeze({ readJson, setText, escapeHtml })",
        "window.ZHILINK_UI_V4_HELPERS_READY = true",
    ):
        assert marker in runtime
    assert "ensureStylesheet" not in runtime

    for filename in ("ui-v4-shell.js", "ui-v4-dashboard.js"):
        source = (ASSETS / filename).read_text(encoding="utf-8")
        assert "window.ZHILINK_UI_V4_HELPERS" in source
        assert "function readJson(raw, fallback)" not in source
        assert "function setText(element, value)" not in source
        assert "escapeHtml: safe" in source
        assert '.replaceAll("&", "&amp;")' not in source

    for filename in (
        "ui-v4-overlays.js",
        "ui-v4-forms.js",
        "ui-v4-results.js",
        "ui-v4-states.js",
        "ui-v4-final-qa.js",
    ):
        source = (ASSETS / filename).read_text(encoding="utf-8")
        assert "window.ZHILINK_UI_V4_HELPERS" not in source, filename


def test_runtime_owns_the_shared_v4_module_catalogue() -> None:
    runtime = RUNTIME.read_text(encoding="utf-8")

    assert "const modules = Object.freeze({" in runtime
    assert 'home: Object.freeze({ label: "工作首页", group: "工作台", icon: "home", resultLabel: "" })' in runtime
    assert 'meeting: Object.freeze({ label: "会议纪要", group: "业务处理", icon: "meeting", resultLabel: "会议纪要 · AI 生成结果" })' in runtime
    assert 'landing: Object.freeze({ label: "实施计划", group: "资料与执行", icon: "plan", resultLabel: "实施计划 · AI 生成结果" })' in runtime
    assert 'report: Object.freeze({ label: "报告归档", group: "归档", icon: "report", resultLabel: "运营报告 · 汇总与导出" })' in runtime
    assert 'const moduleOrder = Object.freeze(["meeting", "contract", "policy", "match", "profile", "landing"])' in runtime
    assert "    modules," in runtime
    assert "    moduleOrder," in runtime


def test_ui_owners_consume_shared_module_catalogue_without_redeclaring_it() -> None:
    shell = (ASSETS / "ui-v4-shell.js").read_text(encoding="utf-8")
    dashboard = (ASSETS / "ui-v4-dashboard.js").read_text(encoding="utf-8")
    final_qa = (ASSETS / "ui-v4-final-qa.js").read_text(encoding="utf-8")

    assert "const MODULES = contracts.modules" in shell
    assert "const MODULES = contracts.modules" in dashboard
    assert "const MODULE_ORDER = contracts.moduleOrder" in dashboard
    assert "const SHARED_MODULES = contracts.modules" in final_qa

    assert "const MODULES = {" not in shell
    assert 'home: { label: "工作首页"' not in shell
    assert 'const MODULE_ORDER = ["meeting"' not in dashboard
    assert 'key === "landing" ? "plan" : key' not in dashboard
    assert "resultLabel:" not in final_qa
    assert 'icon: "meeting"' not in final_qa
    assert 'result.setAttribute("aria-label", shared.resultLabel)' not in final_qa
    assert 'input.setAttribute("aria-label"' not in final_qa
    assert ':scope > .result-panel' not in final_qa
    assert 'document.querySelectorAll(".ui-v4-business-page[id]").forEach(page =>' in final_qa
    assert "ICONS[shared.icon]" in final_qa


def test_contract_consumers_do_not_redeclare_shared_storage_or_event_literals() -> None:
    consumers = (
        "example-loader.js",
        "project-storage.js",
        "data-provenance-guard.js",
        "ui-v4-shell.js",
        "ui-v4-dashboard.js",
        "ui-v4-final-qa.js",
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


def test_project_storage_persists_trust_metadata_without_request_hook() -> None:
    source = (ASSETS / "project-storage.js").read_text(encoding="utf-8")

    assert not (ASSETS / "project-result-meta.js").exists()
    assert 'const PERSISTED_META_FIELDS = ["origin", "example_key", "result_schema_version"]' in source
    assert "PERSISTED_META_FIELDS.forEach(field =>" in source
    assert 'cleaned[field] = current.slice(0, 200)' in source
    assert "meta: cleanMeta(state.meta)" in source


def test_dashboard_and_provenance_share_core_result_catalogue() -> None:
    dashboard = (ASSETS / "ui-v4-dashboard.js").read_text(encoding="utf-8")
    provenance = (ASSETS / "data-provenance-guard.js").read_text(encoding="utf-8")

    assert "const RESULT_KEYS = contracts.resultKeys" in dashboard
    assert "const RESULT_TITLES = contracts.resultTitles" in dashboard
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
