from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEW_SOURCE = ROOT / "frontend" / "assets" / "meeting-user-view.js"


def _sanitize_with_browser_script(markdown: str) -> str:
    source = VIEW_SOURCE.read_text(encoding="utf-8")
    script = f"""
global.window = {{
  ZHILINK_WORKSPACE_CONTRACTS: {{ events: {{ resultUpdated: 'result', structuredUpdated: 'structured', reviewUpdated: 'review' }} }},
  ZHILINK_WORKSPACE_HOOKS: {{ register() {{}} }},
  addEventListener() {{}},
}};
global.state = {{ results: {{ meeting: '' }} }};
global.document = {{
  getElementById(id) {{ return id === 'meetingSourceDialog' ? {{}} : null; }},
  addEventListener() {{}},
  body: {{ appendChild() {{}} }},
}};
eval({json.dumps(source)});
process.stdout.write(window.ZHILINK_MEETING_USER_VIEW.sanitize({json.dumps(markdown)}));
"""
    completed = subprocess.run(
        ["node", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def test_meeting_view_removes_empty_backtick_placeholders_from_saved_results() -> None:
    raw = """## 关键决策
| 事项 | 待确认信息 |
|---|---|
| 运营组织协调 | 是否经管理层书面确认（待确认 ``） |
| 宣传计划 | 预算额度、KPI口径（ `` ） |

## 待确认信息
- ``：活动总预算、商户费用分摊比例、结算周期具体天数
- AI工具配置所需权限范围（``）
- 数据字段 `customer_id` 的用途待确认
"""

    cleaned = _sanitize_with_browser_script(raw)

    assert "``" not in cleaned
    assert "（ ）" not in cleaned
    assert "（``）" not in cleaned
    assert "- ：" not in cleaned
    assert "是否经管理层书面确认（待确认）" in cleaned
    assert "预算额度、KPI口径" in cleaned
    assert "- 活动总预算、商户费用分摊比例、结算周期具体天数" in cleaned
    assert "AI工具配置所需权限范围" in cleaned
    assert "`customer_id`" in cleaned


def test_meeting_cleanup_is_used_by_display_copy_and_export_pipeline() -> None:
    source = VIEW_SOURCE.read_text(encoding="utf-8")

    assert "cleanMeetingMarkdownArtifacts" in source
    assert "stripHiddenSections(cleanMeetingMarkdownArtifacts(markdown))" in source
    assert "tools.copyText(sanitizeMeetingMarkdown(rawMeeting()))" in source
    assert 'hooks.register("results:collect", sanitizeCollectedResults)' in source
