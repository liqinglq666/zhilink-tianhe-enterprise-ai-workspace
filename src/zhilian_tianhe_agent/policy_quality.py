# -*- coding: utf-8 -*-
"""Quality gates for official policy retrieval results.

The crawler can prove that a page came from an allowlisted government domain, but
it cannot prove legal validity or applicant eligibility. This module normalizes
candidate pages before they are sent to the model so weak or misleading pages do
not look like confirmed policy conclusions.
"""
from __future__ import annotations

import re
from typing import Any, Mapping
from urllib.parse import urlparse, urlunparse

from .policy_retrieval import OfficialPolicyRetrieval, OfficialPolicySource

_DOMAIN_TERMS = (
    "人工智能", "AI", "大模型", "模型服务", "算力", "算法", "软件", "互联网",
    "数字化", "数字服务", "数据安全", "科技", "创新", "创业", "青年", "港澳",
    "台湾", "商贸", "消费", "商圈", "企业服务", "专业服务", "融资", "金融",
    "知识产权", "园区", "中小企业", "小微企业", "人才", "高新技术企业",
)

_HARD_TOPIC_TERMS = (
    "铁路", "轨道交通", "安全保护区", "征地", "拆迁", "水利", "农业", "林业",
    "医疗", "教育招生", "体育赛事", "住房保障", "垃圾分类", "防汛", "消防",
)

_BREADCRUMB_MARKERS = ("天河政策 ", "政策解读 ", "政策文件 ")


def refine_policy_retrieval(
    retrieval: OfficialPolicyRetrieval,
    profile: Mapping[str, Any] | None,
    demand: str = "",
) -> OfficialPolicyRetrieval:
    """Normalize, rank and filter candidate official pages.

    The returned object keeps the existing schema. `status=active` remains a
    crawler inference and must still be described to users as pending manual
    verification.
    """

    query = _space(" ".join([
        demand,
        *(
            _space((profile or {}).get(key))
            for key in ("industry", "location", "stage", "demands", "name")
        ),
    ]))
    normalized: list[tuple[int, OfficialPolicySource]] = []
    removed = 0

    for source in retrieval.sources:
        item = _normalize_source(source)
        score = _relevance_score(item, query)
        if _should_keep(item, query, score):
            normalized.append((score, item))
        else:
            removed += 1

    normalized.sort(
        key=lambda pair: (
            pair[0],
            pair[1].status == "active",
            pair[1].source_kind == "政策文件",
            pair[1].published_at,
            pair[1].title,
        ),
        reverse=True,
    )

    selected = [
        source.model_copy(update={"citation_id": f"POL-{index:03d}"})
        for index, (_, source) in enumerate(normalized[:6], start=1)
    ]

    warnings = list(dict.fromkeys(retrieval.warnings))
    if removed:
        warnings.append(f"已过滤 {removed} 个与当前需求关联度不足或原文质量过低的候选页面。")
    if selected:
        warnings.append("页面状态为系统规则初判，不等同于政策有效性确认；正式使用前必须打开原文人工核验。")
        status = "partial" if warnings else "ok"
    elif retrieval.status in {"unavailable", "disabled"}:
        status = retrieval.status
    else:
        status = "no_results"
        warnings.append("未保留可作为当前政策准备依据的高相关官方候选页面。")

    return retrieval.model_copy(update={
        "status": status,
        "warnings": list(dict.fromkeys(warnings))[:30],
        "sources": selected,
    })


def _normalize_source(source: OfficialPolicySource) -> OfficialPolicySource:
    title = _clean_title(source.title)
    excerpt = _clean_excerpt(source.excerpt)
    issuer = _space(source.issuer)
    if issuer in {"本网", "本网站", "网站"}:
        issuer = ""
    return source.model_copy(update={
        "title": title,
        "excerpt": excerpt,
        "issuer": issuer,
        "official_url": _https_official_url(source.official_url),
    })


def _clean_title(value: str) -> str:
    title = _space(value)
    if title.startswith("您当前所在的位置"):
        for marker in _BREADCRUMB_MARKERS:
            if marker in title:
                title = title.rsplit(marker, 1)[-1].strip()
                break
        else:
            parts = re.split(r"[>＞]", title)
            title = parts[-1].strip() if parts else title

    title = re.sub(r"^【[^】]{1,40}】\s*", "", title)
    for anchor in ("关于印发", "关于废止", "关于延长", "关于《", "关于<"):
        position = title.find(anchor)
        if position > 0:
            title = title[position:]
            break

    if "于印发" in title and "关于印发" not in title:
        title = "关于印发" + title.split("于印发", 1)[1]

    for suffix in (
        " - 广州市人民政府门户网站",
        " - 广州市天河区人民政府门户网站",
        "_广州市人民政府门户网站",
    ):
        if title.endswith(suffix):
            title = title[: -len(suffix)].strip()
    return title[:500]


def _clean_excerpt(value: str) -> str:
    excerpt = _space(value)
    if excerpt.startswith("您当前所在的位置"):
        position = excerpt.find("：")
        if position >= 0:
            excerpt = excerpt[position + 1 :].strip()
    if "主办：广州市天河区人民政府" in excerpt and len(excerpt) < 260:
        return ""
    return excerpt[:500]


def _https_official_url(raw: str) -> str:
    try:
        parsed = urlparse(raw)
    except ValueError:
        return raw
    host = (parsed.hostname or "").lower()
    if not host:
        return raw
    if host == "thnet.gov.cn" or host.endswith(".thnet.gov.cn"):
        return urlunparse(parsed._replace(scheme="https", netloc=host + ((f":{parsed.port}") if parsed.port and parsed.port != 80 else "")))
    if parsed.scheme == "http" and any(
        host == suffix or host.endswith("." + suffix)
        for suffix in ("gov.cn", "gd.gov.cn", "gz.gov.cn")
    ):
        return urlunparse(parsed._replace(scheme="https", netloc=host))
    return raw


def _relevance_score(source: OfficialPolicySource, query: str) -> int:
    text = _space(f"{source.title} {source.excerpt}")
    score = 0
    for term in _DOMAIN_TERMS:
        if term.lower() in query.lower() and term.lower() in text.lower():
            score += 4 if len(term) >= 4 else 2
    if source.document_number:
        score += 1
    if source.issuer:
        score += 1
    if source.excerpt:
        score += 2
    if source.source_kind == "政策文件":
        score += 1
    if source.status == "active":
        score += 1
    return score


def _should_keep(source: OfficialPolicySource, query: str, score: int) -> bool:
    text = _space(f"{source.title} {source.excerpt}")
    if not source.title or not source.official_url:
        return False
    if not source.excerpt and not source.document_number:
        return False
    for topic in _HARD_TOPIC_TERMS:
        if topic in text and topic not in query:
            return False
    if source.source_kind == "政策解读" and source.status in {"revoked", "expired", "suspended"}:
        return score >= 8
    if source.status in {"revoked", "expired", "suspended"}:
        return score >= 6
    if source.status == "unknown":
        return score >= 5
    return score >= 4


def _space(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
