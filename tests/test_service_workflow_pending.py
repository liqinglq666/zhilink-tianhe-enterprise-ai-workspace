from backend.service_workflow_store import pending


def test_negative_pending_placeholders_are_ignored() -> None:
    results = {
        "meeting": "## 待确认信息\n- 暂无待确认事项。\n- 待确认事项：无",
        "policy": "## 未决事项\n- 没有未决问题。\n- 未决信息：暂无",
    }

    assert pending(results) == []


def test_real_pending_items_are_preserved() -> None:
    results = {
        "meeting": "## 待确认信息\n- 企业联系人待确认。\n- 无其他问题，但负责人待确认。",
        "policy": "## 未决事项\n- 未决：付款节点需补充。",
    }

    items = pending(results)

    assert [item["text"] for item in items] == [
        "企业联系人待确认。",
        "无其他问题，但负责人待确认。",
        "未决：付款节点需补充。",
    ]
