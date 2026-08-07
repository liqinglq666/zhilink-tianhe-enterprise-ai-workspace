from __future__ import annotations

from datetime import datetime, timezone

from zhilian_tianhe_agent.official_policy import OfficialPolicyAgent
from zhilian_tianhe_agent.policy_quality import audit_policy_output, refine_policy_retrieval
from zhilian_tianhe_agent.policy_retrieval import OfficialPolicyRetrieval, OfficialPolicySource


def make_source(
    citation_id: str,
    title: str,
    url: str,
    *,
    status: str = "unknown",
    excerpt: str = "",
    issuer: str = "本网",
    document_number: str = "",
    source_kind: str = "政策文件",
    expires_at: str = "",
) -> OfficialPolicySource:
    return OfficialPolicySource(
        citation_id=citation_id,
        title=title,
        official_url=url,
        official_domain="www.thnet.gov.cn",
        source_kind=source_kind,
        issuer=issuer,
        document_number=document_number,
        published_at="",
        effective_at="",
        expires_at=expires_at,
        status=status,
        excerpt=excerpt,
        content_sha256="a" * 64,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )


def sample_retrieval() -> OfficialPolicyRetrieval:
    return OfficialPolicyRetrieval(
        query="人工智能 企业服务 青年创业 数字化",
        status="ok",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        searched_catalogs=["https://www.thnet.gov.cn/zjth/tzth/tzzc/thzc/"],
        warnings=[],
        sources=[
            make_source(
                "POL-001",
                "您当前所在的位置：首页 > 营商环境 > 政策文件 > 天河政策 关于推动人工智能赋能中小企业数字化转型的工作指引",
                "http://www.thnet.gov.cn/zjth/tzth/tzzc/thzc/content/post_10000001.html",
                status="active",
                excerpt="支持中小企业应用人工智能和数字化工具改善经营管理，并鼓励服务机构提供可核验的数字化解决方案。",
                issuer="广州市天河区科技工业和信息化局",
                document_number="穗天科工信规字〔2026〕1号",
                expires_at="2026-12-31",
            ),
            make_source(
                "POL-002",
                "关于印发广州市天河区加快推动金融服务实体经济高质量发展的若干政策措施的通知",
                "http://www.thnet.gov.cn/zjth/tzth/tzzc/thzc/content/post_10163873.html",
                status="active",
                excerpt="探索组建天河区科技金融联盟，为科技型企业提供多元化金融服务和融资对接支持。",
                issuer="广州市天河区商务局",
                document_number="穗天商务规字〔2025〕2号",
                expires_at="2026-12-31",
            ),
            make_source(
                "POL-003",
                "关于印发广州市天河区推动港澳青年创新创业发展实施办法的通知",
                "http://www.thnet.gov.cn/zjth/tzth/tzzc/thzc/content/post_3763195.html",
                status="unknown",
                excerpt="广州市天河区推动港澳青年创新创业发展实施办法的通知.pdf",
            ),
            make_source(
                "POL-004",
                "关于延长广佛环线安全保护区通告有效期的政策解读",
                "http://www.thnet.gov.cn/zwgk/zcjd/content/post_10877363.html",
                status="unknown",
                excerpt="为加强城际铁路安全管理，保障人民群众生命财产安全和铁路运输安全。",
                issuer="广州市天河区人民政府",
                source_kind="政策解读",
            ),
            make_source(
                "POL-005",
                "关于废止穗天科工信规〔2018〕1号文的通知",
                "http://www.thnet.gov.cn/zjth/tzth/tzzc/thzc/content/post_8819774.html",
                status="revoked",
                excerpt="本通知决定废止原有科技和信息化专项资金管理文件，自公布之日起不再执行。",
                document_number="穗天政数规字〔2022〕1号",
            ),
        ],
    )


def test_refine_policy_retrieval_requires_direct_business_relevance() -> None:
    refined = refine_policy_retrieval(
        sample_retrieval(),
        {"industry": "企业服务、人工智能应用", "location": "天河区"},
        "关注人工智能、行业大模型、企业数字化转型和青年创业政策方向",
    )

    assert refined.status == "partial"
    assert len(refined.sources) == 1
    assert refined.sources[0].citation_id == "POL-001"
    assert "人工智能" in refined.sources[0].title
    assert refined.sources[0].official_url.startswith("https://www.thnet.gov.cn/")
    assert all("金融服务实体经济" not in item.title for item in refined.sources)
    assert all("港澳青年" not in item.title for item in refined.sources)
    assert all("广佛环线" not in item.title for item in refined.sources)
    assert all(item.status != "revoked" for item in refined.sources)
    assert any("特定身份" in warning for warning in refined.warnings)
    assert any("不代表业务直接适配" in warning for warning in refined.warnings)


def test_specific_audience_policy_requires_explicit_identity_terms() -> None:
    retrieval = OfficialPolicyRetrieval(
        query="港澳青年创业",
        status="ok",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        searched_catalogs=[],
        warnings=[],
        sources=[
            make_source(
                "POL-001",
                "广州市天河区推动港澳青年创新创业发展实施办法",
                "https://www.thnet.gov.cn/policy/1.html",
                excerpt="本办法支持符合条件的港澳青年在天河区开展创新创业活动，并规定申请主体和办理程序。",
            )
        ],
    )

    generic = refine_policy_retrieval(retrieval, {}, "服务青年创业团队")
    explicit = refine_policy_retrieval(retrieval, {}, "团队创始人为香港青年，查询港澳青年创业政策")

    assert generic.sources == []
    assert len(explicit.sources) == 1


def test_policy_output_audit_replaces_status_and_overclaim_sections() -> None:
    refined = refine_policy_retrieval(
        sample_retrieval(),
        {"industry": "人工智能企业服务"},
        "人工智能和数字化转型",
    )
    model_output = """## 一句话结论
发现1项高度相关且status=active的政策，企业存在申报基础。

## 检索状态与范围
| 项目 | 内容 |
|---|---|
| 适用边界 | 仅限天河区注册经营主体 |

## 官方候选来源
| 编号 | 状态 |
|---|---|
| POL-001 | active |

## 材料准备清单
建议准备等保二级/三级认证、算法备案、ARPU值、审计报告、完税证明、社保缴纳记录。
"""

    checked = audit_policy_output(model_output, refined)

    assert "AI 初步判断：" in checked
    assert "高度相关" not in checked
    assert "status=active" not in checked
    assert "存在申报基础" not in checked
    assert "边界说明" in checked
    assert "不代表适用区域" in checked
    assert "系统初判有效，待人工核验" in checked
    assert "等保二级/三级" not in checked
    assert "算法备案" not in checked
    assert "ARPU值" not in checked
    assert "## 自动一致性校验" in checked


class FakeRetriever:
    def search(self, profile, demand):
        return sample_retrieval()


class FakeLlm:
    def chat(self, system_prompt, prompt):
        assert "不得使用“高度相关" in prompt
        assert "特定人群政策" in prompt
        assert "不得擅自要求等保等级" in prompt
        return """## 一句话结论
发现高度相关且active的候选来源。

## 检索状态与范围
待模型填写。

## 官方候选来源
待模型填写。
"""

    def chat_stream(self, system_prompt, prompt):
        yield "## 一句话结论\n"
        yield "发现高度相关且active的候选来源。\n\n"
        yield "## 检索状态与范围\n待模型填写。\n\n"
        yield "## 官方候选来源\n待模型填写。"


def test_official_policy_agent_audits_run_and_stream_without_duplicate_appendices() -> None:
    agent = OfficialPolicyAgent(FakeLlm(), FakeRetriever())
    result = agent.run(
        {"industry": "企业服务、人工智能应用", "location": "天河区"},
        "关注人工智能、企业数字化转型和青年创业政策方向",
    )

    assert result.content.count("## 一句话结论") == 1
    assert "高度相关" not in result.content
    assert "active" not in result.content
    assert "## 自动一致性校验" in result.content
    assert "输入证据与待确认索引" not in result.content
    assert "官方政策来源与原文引用" not in result.content
    assert "政策检索边界" not in result.content
    assert "官方候选来源与人工核验" in result.mode

    chunks, _ = agent.stream(
        {"industry": "企业服务、人工智能应用"},
        "人工智能和数字化转型",
    )
    streamed = "".join(chunks)
    assert "高度相关" not in streamed
    assert "active" not in streamed
    assert "## 自动一致性校验" in streamed
    assert "## 官方候选来源" in streamed
