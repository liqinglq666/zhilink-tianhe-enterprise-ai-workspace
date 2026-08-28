from __future__ import annotations

from zhilian_tianhe_agent.structured_output import structure_markdown


def test_wide_markdown_tables_are_truncated_to_schema_width() -> None:
    columns = [f"列{index}" for index in range(25)]
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    row = "| " + " | ".join(f"值{index}" for index in range(25)) + " |"
    content = f"## 一句话结论\n正常。[MT-01]\n\n## 关键决策\n{header}\n{separator}\n{row}"

    result = structure_markdown("meeting", content)
    table = result.sections[1].table

    assert table is not None
    assert len(table.columns) == 20
    assert len(table.rows[0]) == 20
    assert table.columns[-1] == "列19"
    assert table.rows[0][-1] == "值19"


def test_evidence_collections_are_bounded_instead_of_raising_validation_errors() -> None:
    all_ids = [f"CR-A{index:03d}" for index in range(600)]
    item_ids = [f"CR-B{index:03d}" for index in range(40)]
    content = (
        "## 一句话结论\n"
        + " ".join(all_ids)
        + "\n\n## 待确认信息\n- 待确认 "
        + " ".join(item_ids)
    )

    result = structure_markdown("meeting", content)

    assert len(result.evidence_ids) == 500
    assert len(result.sections[0].evidence_ids) == 100
    assert result.pending_confirmations
    assert len(result.pending_confirmations[0].evidence_ids) == 30
