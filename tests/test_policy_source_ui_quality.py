from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_policy_source_ui_uses_candidate_language_and_new_cache() -> None:
    script = (ROOT / "frontend" / "assets" / "policy-sources.js").read_text(encoding="utf-8")

    assert "zhilian_official_policy_sources_v3" in script
    assert "候选来源初筛完成" in script
    assert "系统初判有效 · 待核验" in script
    assert "系统初判已废止 · 不可作现行依据" in script
    assert "状态待人工核验" in script
    assert "通过初筛的候选来源" in script
    assert "可核验的直接相关候选来源" in script
    assert "打开 HTTPS 官方原文" in script
    assert "官方检索成功" not in script
    assert "高相关候选来源" not in script
    assert "active</strong>" not in script
    assert "有效期至 ${source.expires_at}" not in script


def test_policy_backend_filters_search_and_generation_consistently() -> None:
    route = (ROOT / "backend" / "policy_official_routes.py").read_text(encoding="utf-8")
    agent = (ROOT / "src" / "zhilian_tianhe_agent" / "official_policy.py").read_text(encoding="utf-8")
    quality = (ROOT / "src" / "zhilian_tianhe_agent" / "policy_quality.py").read_text(encoding="utf-8")

    assert "refine_policy_retrieval(raw, profile, payload.demand)" in route
    assert "retrieval = refine_policy_retrieval(raw_retrieval, profile, demand)" in agent
    assert "audit_policy_output(raw_content, prepared.retrieval)" in agent
    assert 'raw_content = "".join(self.llm.chat_stream' in agent
    assert "_RESTRICTED_AUDIENCES" in quality
    assert "_has_substantive_excerpt" in quality
    assert "_retrieval_section" in quality
    assert "_sources_section" in quality
    assert "yield \"\\n\\n\" + prepared.input_evidence.to_markdown()" not in agent
    assert "yield \"\\n\\n\" + prepared.retrieval.to_markdown()" not in agent
