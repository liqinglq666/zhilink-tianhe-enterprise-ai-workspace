from backend.service_workflow_guards import safe_official_references


def test_policy_reference_keeps_only_trusted_government_https_urls():
    markdown = """
| 引用编号 | 政策文件 | 官方原文 |
|---|---|---|
| POL-001 | 天河企业服务措施 | [原文](https://www.thnet.gov.cn/policy/1.html) |
| POL-002 | 伪造政策链接 | [原文](https://evil.example/policy) |
| POL-003 | 降级链接 | [原文](http://www.gz.gov.cn/policy/3.html) |
"""
    items = {item["citation_id"]: item for item in safe_official_references(markdown)}
    assert items["POL-001"]["official_url"] == "https://www.thnet.gov.cn/policy/1.html"
    assert items["POL-002"]["official_url"] == ""
    assert items["POL-003"]["official_url"] == ""
