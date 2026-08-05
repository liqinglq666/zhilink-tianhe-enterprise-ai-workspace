from __future__ import annotations

from pathlib import Path

from zhilian_tianhe_agent.policy_retrieval import OfficialPolicyRetriever

CATALOG = "https://www.thnet.gov.cn/zjth/tzth/tzzc/thzc/"
ACTIVE_URL = "https://www.gz.gov.cn/gfxwj/qjgfxwj/thq/qbm/content/post_10234100.html"
REVOKED_URL = "https://www.thnet.gov.cn/zwgk/zcwj/expired.html"

CATALOG_HTML = f"""
<html><body>
<a href="{ACTIVE_URL}">广州市天河区加快培育个体工商户和小微企业转型升级的若干政策措施</a>
<a href="{REVOKED_URL}">关于废止软件产业支持政策的通知</a>
<a href="https://evil.example/policy">虚假政策补贴通知</a>
</body></html>
"""
ACTIVE_HTML = """
<html><head><title>小微企业转型升级政策 - 广州市人民政府门户网站</title></head><body>
<h1>广州市天河区加快培育个体工商户和小微企业转型升级的若干政策措施</h1>
<p>文号：穗天发改规字〔2025〕2号</p>
<p>实施日期：2025年04月24日</p><p>失效日期：2027年01月01日</p>
<p>发布机关：广州市天河区发展和改革局</p>
<p>对当年度个体工商户首次达到软件业企业标准的，给予2万元支持。</p>
</body></html>
"""
REVOKED_HTML = """
<html><body><h1>广州市天河区科技工业和信息化局关于废止软件产业支持政策的通知</h1>
<p>发布时间：2026年02月14日</p><p>发布机关：广州市天河区科技工业和信息化局</p>
<p>决定废止原软件产业支持政策，自本通知印发之日起停止执行。</p></body></html>
"""


def retriever(mapping=None):
    pages = mapping or {CATALOG: CATALOG_HTML, ACTIVE_URL: ACTIVE_HTML, REVOKED_URL: REVOKED_HTML}

    def fetch(url):
        if url not in pages:
            raise RuntimeError("missing fixture")
        return pages[url]

    return OfficialPolicyRetriever(
        catalog_urls=[CATALOG],
        allowed_domain_suffixes=["thnet.gov.cn", "gz.gov.cn"],
        fetcher=fetch,
    )


def test_official_search_extracts_metadata_excerpt_and_hash(monkeypatch):
    monkeypatch.setenv("POLICY_MAX_CATALOG_PAGES", "1")
    result = retriever().search({"industry": "软件业", "location": "天河区"}, "小微企业转型升级", limit=2)
    assert result.status == "ok"
    assert result.sources[0].citation_id == "POL-001"
    assert result.sources[0].official_domain.endswith("gz.gov.cn")
    assert result.sources[0].document_number == "穗天发改规字〔2025〕2号"
    assert result.sources[0].effective_at == "2025-04-24"
    assert result.sources[0].expires_at == "2027-01-01"
    assert "2万元支持" in result.sources[0].excerpt
    assert len(result.sources[0].content_sha256) == 64


def test_revoked_policy_is_not_marked_active(monkeypatch):
    monkeypatch.setenv("POLICY_MAX_CATALOG_PAGES", "1")
    result = retriever().search({"industry": "软件"}, "废止 软件 政策", limit=2)
    revoked = next(item for item in result.sources if "废止" in item.title)
    assert revoked.status == "revoked"


def test_catalog_cannot_escape_official_allowlist(monkeypatch):
    monkeypatch.setenv("POLICY_MAX_CATALOG_PAGES", "1")
    result = retriever().search({}, "政策补贴", limit=6)
    assert all("evil.example" not in item.official_url for item in result.sources)


def test_no_results_is_explicit(monkeypatch):
    monkeypatch.setenv("POLICY_MAX_CATALOG_PAGES", "1")
    empty = retriever({CATALOG: "<html><body><a href='/about'>联系我们</a></body></html>"})
    result = empty.search({}, "量子航运专项", limit=3)
    assert result.status == "no_results"
    assert result.sources == []
    assert result.warnings


def test_same_query_uses_deterministic_cache(monkeypatch):
    monkeypatch.setenv("POLICY_MAX_CATALOG_PAGES", "1")
    calls = []
    pages = {CATALOG: CATALOG_HTML, ACTIVE_URL: ACTIVE_HTML, REVOKED_URL: REVOKED_HTML}

    def fetch(url):
        calls.append(url)
        return pages[url]

    service = OfficialPolicyRetriever(
        catalog_urls=[CATALOG],
        allowed_domain_suffixes=["thnet.gov.cn", "gz.gov.cn"],
        fetcher=fetch,
    )
    first = service.search({"industry": "软件"}, "转型升级", limit=2)
    count = len(calls)
    second = service.search({"industry": "软件"}, "转型升级", limit=2)
    assert first == second
    assert len(calls) == count


def test_markdown_contains_official_links_and_boundaries(monkeypatch):
    monkeypatch.setenv("POLICY_MAX_CATALOG_PAGES", "1")
    markdown = retriever().search({"industry": "软件"}, "小微企业", limit=1).to_markdown()
    assert "## 官方政策来源与原文引用" in markdown
    assert "[POL-001]" in markdown
    assert "打开官方原文" in markdown
    assert "不代表企业自动符合申报条件" in markdown


def test_frontend_extension_switches_to_grounded_route():
    root = Path(__file__).resolve().parents[1]
    script = (root / "frontend/assets/policy-sources.js").read_text(encoding="utf-8")
    assert "ZHILINK_POLICY_SOURCES_READY" in script
    assert "/api/policy/official/search" in script
    assert "/api/policy/official/stream" in script
