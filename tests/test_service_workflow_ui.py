from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "frontend" / "assets" / "service-workflow.js"


def test_service_workflow_has_unique_dialog_and_form_title_ids() -> None:
    source = SERVICE.read_text(encoding="utf-8")

    assert 'aria-labelledby="swDialogTitle"' in source
    assert '<h2 id="swDialogTitle">事项进度与责任协作</h2>' in source
    assert source.count('id="swTitle"') == 1


def test_service_workflow_hides_internal_provenance_details_at_source() -> None:
    source = SERVICE.read_text(encoding="utf-8")

    for forbidden in (
        "swKb",
        "知识库发布版本引用",
        "上下文 SHA-256",
        "payload_sha256.slice",
        'link[data-service-workflow]',
        "service-workflow.css",
    ):
        assert forbidden not in source

    assert "knowledge_citations: recentKnowledgeCitations()" in source
    assert "existingKnowledgeCitations()" in source
    assert "更新办理依据" in source


def test_service_workflow_source_owns_business_copy() -> None:
    source = SERVICE.read_text(encoding="utf-8")

    for expected in (
        "服务跟进",
        "事项进度与责任协作",
        "当前办理依据",
        "项目材料",
        "官方政策",
        "组织知识",
        "待确认",
        "操作记录",
    ):
        assert expected in source
