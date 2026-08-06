from __future__ import annotations

from datetime import datetime, timezone

from zhilian_tianhe_agent.official_policy import OfficialPolicyAgent
from zhilian_tianhe_agent.policy_quality import refine_policy_retrieval
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
        query="人工智能 科技服务 青年创业 数字化",
        status="ok",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        searched_catalogs=["https://www.thnet.gov.cn/zjth/tzth/tzzc/thzc/"],
        warnings=[],
        sources=[
            make_source(
                "POL-001",
                "您当前所在的位置：首页 > 营商环境 > 政策文件 > 天河政策 广州市天河区商务局于印发广州市天河区加快推动金融服务实体经济高质量发展的若干政策措施的通知",
                "http://www.thnet.gov.cn/zjth/tzth/tzzc/thzc/content/post_10163873.html",
                status="active",
                excerpt="探索组建天河区科技金融联盟，为科技型企业提供多元化金融服务。",
                issuer="广州市天河区商务局",
                document_number="穗天商务规字〔2025〕2号",
                expires_at="2026-12-31",
            ),
            make_source(
                "POL-002",
                "您当前所在的位置：首页 > 政务公开 > 政策解读 关于延长广佛环线安全保护区通告有效期的政策解读",
                "http://www.thnet.gov.cn/zwgk/zcjd/content/post_10877363.html",
                status="unknown",
                excerpt="为加强城际铁路安全管理，保障铁路运输安全。",
                issuer="广州市天河区人民政府",
                source_kind="政策解读",
            ),
            make_source(
                "POL-003",
                "您当前所在的位置：首页 > 营商环境 > 政策文件 > 天河政策 广州市天河区科技工业和信息化局关于印发广州市天河区推动港澳青年创新创业发展实施办法的通知",
                "http://www.thnet.gov.cn/zjth/tzth/tzzc/thzc/content/post_3763195.html",
                status="unknown",
                excerpt="广州市天河区推动港澳青年创新创业发展实施办法的通知.pdf",
            ),
            make_source(
                "POL-004",
                "您当前所在的位置：首页 > 营商环境 > 政策文件 > 天河政策 广州市天河区政务服务数据管理局关于废止穗天科工信规〔2018〕1号文的通知",
                "http://www.thnet.gov.cn/zjth/tzth/tzzc/thzc/content/post_8819774.html",
                status="revoked",
                excerpt="主办：广州市天河区人民政府 承办：广州市天河区政务服务和数据管理局",
                document_number="穗天政数规字〔2022〕1号",
            ),
        ],
    )


def test_refine_policy_retrieval_cleans_and_filters_candidates() -> None:
    refined = refine_policy_retrieval(
        sample_retrieval(),
        {"industry": "企业服务、人工智能应用", "location": "天河区"},
        "关注人工智能、科技服务、数字化和青年创业政策方向",
    )

    assert refined.status == "partial"
    assert [item.citation_id for item in refined.sources] == [
        f"POL-{index:03d}" for index in range(1, len(refined.sources) + 1)
    ]
    assert all(item.official_url.startswith("https://www.thnet.gov.cn/") for item in refined.sources)
    assert all(not item.title.startswith("您当前所在的位置") for item in refined.sources)
    assert all("广佛环线" not in item.title for item in refined.sources)
    assert all("穗天科工信规" not in item.title for item in refined.sources)
    assert any(item.status == "active" for item in refined.sources)
    assert any("过滤" in warning for warning in refined.warnings)
    assert any("人工核验" in warning for warning in refined.warnings)


class FakeRetriever:
    def search(self, profile, demand):
        return sample_retrieval()


class FakeLlm:
    def chat(self, system_prompt, prompt):
        assert "禁止写成“已确认现行有效”" in prompt
        assert "不要在报告末尾重复输出" in prompt
        return "## 一句话结论\n仅发现待人工核验的官方候选来源。"

    def chat_stream(self, system_prompt, prompt):
        yield "## 一句话结论\n"
        yield "仅发现待人工核验的官方候选来源。"


def test_official_policy_agent_does_not_append_duplicate_evidence_sections() -> None:
    agent = OfficialPolicyAgent(FakeLlm(), FakeRetriever())
    result = agent.run(
        {"industry": "企业服务、人工智能应用", "location": "天河区"},
        "关注人工智能、科技服务、数字化和青年创业政策方向",
    )

    assert result.content.count("## 一句话结论") == 1
    assert "输入证据与待确认索引" not in result.content
    assert "官方政策来源与原文引用" not in result.content
    assert "政策检索边界" not in result.content
    assert "官方候选来源与人工核验" in result.mode


def test_official_policy_stream_contains_only_model_output() -> None:
    agent = OfficialPolicyAgent(FakeLlm(), FakeRetriever())
    chunks, _ = agent.stream({}, "人工智能政策")
    content = "".join(chunks)

    assert content == "## 一句话结论\n仅发现待人工核验的官方候选来源。"
    assert "官方政策来源与原文引用" not in content
