# -*- coding: utf-8 -*-
"""Quality gates and output boundaries for official policy candidates.

An allowlisted government page proves provenance only. It does not prove that a
policy is current, that an applicant belongs to the supported group, or that a
project is eligible. Retrieval therefore uses semantic relevance separately from
page quality, and generated reports are audited before presentation.
"""
from __future__ import annotations

import re
from typing import Any, Mapping
from urllib.parse import urlparse, urlunparse

from .policy_retrieval import OfficialPolicyRetrieval, OfficialPolicySource

_STRONG_TERMS = (
    "人工智能", "AI", "大模型", "行业大模型", "模型服务", "算力", "算法",
    "软件", "SaaS", "数字化转型", "数字化", "数字服务", "数据安全",
    "企业服务", "商圈", "促消费", "知识产权", "高新技术企业", "专精特新",
)
_GENERIC_TERMS = (
    "科技", "创新", "创业", "青年", "企业", "中小企业", "小微企业",
    "园区", "人才", "消费", "商贸", "专业服务", "金融", "融资",
)
_FINANCE_TERMS = ("金融", "融资", "贷款", "贴息", "担保", "投资", "基金", "信贷", "资本")
_RESTRICTED_AUDIENCES = {
    "台湾": ("台湾", "台资", "台胞", "台青"),
    "港澳": ("港澳", "香港", "澳门", "港资", "澳资", "港澳青年"),
}
_HARD_TOPIC_TERMS = (
    "铁路", "轨道交通", "安全保护区", "征地", "拆迁", "水利", "农业", "林业",
    "医疗", "教育招生", "体育赛事", "住房保障", "垃圾分类", "防汛", "消防",
)
_BREADCRUMB_MARKERS = ("天河政策 ", "政策解读 ", "政策文件 ")
_STATUS_LABELS = {
    "active": "系统初判有效，待人工核验",
    "expired": "系统初判已到期，待人工核验",
    "revoked": "系统初判已废止，不可作现行依据",
    "suspended": "系统初判暂停实施，待人工核验",
    "unknown": "状态待人工核验",
}
_RETRIEVAL_STATUS_LABELS = {
    "ok": "候选来源初筛完成",
    "partial": "候选来源已过滤，仍需人工核验",
    "no_results": "未保留可核验的直接相关候选来源",
    "unavailable": "官方来源检索暂不可用",
    "disabled": "官方来源检索已关闭",
}


def refine_policy_retrieval(
    retrieval: OfficialPolicyRetrieval,
    profile: Mapping[str, Any] | None,
    demand: str = "",
) -> OfficialPolicyRetrieval:
    """Normalize, semantically rank and conservatively filter official pages."""

    query = _query_text(profile, demand)
    normalized: list[tuple[int, int, OfficialPolicySource]] = []
    removed = 0
    restricted_removed = 0
    weak_content_removed = 0

    for source in retrieval.sources:
        item = _normalize_source(source)
        metrics = _relevance_metrics(item, query)
        keep, reason = _should_keep(item, query, metrics)
        if keep:
            normalized.append((metrics[0], _quality_score(item), item))
        else:
            removed += 1
            if reason == "restricted_audience":
                restricted_removed += 1
            elif reason == "weak_content":
                weak_content_removed += 1

    normalized.sort(
        key=lambda row: (
            row[0],
            row[1],
            row[2].source_kind == "政策文件",
            row[2].published_at,
            row[2].title,
        ),
        reverse=True,
    )
    selected = [
        source.model_copy(update={"citation_id": f"POL-{index:03d}"})
        for index, (_, _, source) in enumerate(normalized[:6], start=1)
    ]

    warnings = list(dict.fromkeys(retrieval.warnings))
    if removed:
        warnings.append(f"已过滤 {removed} 个缺少直接业务关联或正文依据不足的页面。")
    if restricted_removed:
        warnings.append(
            f"其中 {restricted_removed} 个为特定身份或特定人群政策；用户输入未证明具备对应身份，未纳入主候选。"
        )
    if weak_content_removed:
        warnings.append(
            f"其中 {weak_content_removed} 个仅提取到附件名、页脚或过短文本，无法支撑适配分析。"
        )
    if selected:
        warnings.append(
            "保留页面仅通过关键词与正文初筛，不代表业务直接适配、现行有效或具备申报资格；必须打开原文核验。"
        )
        status = "partial"
    elif retrieval.status in {"unavailable", "disabled"}:
        status = retrieval.status
    else:
        status = "no_results"
        warnings.append(
            "本次未保留可核验的直接相关官方候选来源；报告只能给出检索方向和通用准备建议。"
        )

    return retrieval.model_copy(update={
        "status": status,
        "warnings": list(dict.fromkeys(warnings))[:30],
        "sources": selected,
    })


def audit_policy_output(content: str, retrieval: OfficialPolicyRetrieval) -> str:
    """Replace deterministic sections and soften unsupported policy conclusions."""

    result = (content or "").strip()
    if not result:
        return result

    replacements = (
        ("高度相关", "通过关键词与正文初筛"),
        ("高相关官方候选来源", "通过初筛的官方候选来源"),
        ("高相关候选来源", "通过初筛的候选来源"),
        ("存在申报基础", "需进一步核验是否满足申报条件"),
        ("具备申报基础", "需进一步核验是否满足申报条件"),
        ("可初步适配", "需核验适用条件"),
        ("更可能覆盖", "需核验是否覆盖"),
        ("可直接申报", "不得据此判断可直接申报"),
        ("符合申报条件", "是否符合申报条件待官方原文和主管部门确认"),
        ("已确认现行有效", "系统初判有效，待人工核验"),
    )
    for old, new in replacements:
        result = result.replace(old, new)

    for raw, label in _STATUS_LABELS.items():
        result = re.sub(
            rf"(?<![A-Za-z_])(?:status\s*=\s*)?{re.escape(raw)}(?![A-Za-z_])",
            label,
            result,
            flags=re.IGNORECASE,
        )

    result = re.sub(
        r"有效期至\s*(\d{4}-\d{1,2}-\d{1,2})",
        r"页面解析到日期 \1（日期含义待原文核验）",
        result,
    )
    result = re.sub(
        r"expires_at\s*[:=]\s*(\d{4}-\d{1,2}-\d{1,2})",
        r"页面解析到日期 \1（日期含义待原文核验）",
        result,
        flags=re.IGNORECASE,
    )

    cautious_replacements = (
        (r"等保二级\s*/\s*三级(?:认证|测评)?", "适用的数据安全或等级保护要求（具体要求待专业核验）"),
        (r"等保[二三]级(?:认证|测评)?", "适用的数据安全或等级保护要求（具体要求待专业核验）"),
        (r"算法备案", "适用的算法或生成式人工智能合规义务（待专业核验）"),
        (r"ARPU\s*值", "客户与收入指标（具体口径待申报指南确认）"),
        (r"审计报告、完税证明、社保缴纳记录", "财务、纳税或人员证明材料（具体清单待申报指南确认）"),
    )
    for pattern, replacement in cautious_replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    result = _replace_section(result, "检索状态与范围", _retrieval_section(retrieval))
    result = _replace_section(result, "官方候选来源", _sources_section(retrieval))

    if result.startswith("## 一句话结论"):
        lines = result.splitlines()
        for index in range(1, len(lines)):
            if lines[index].strip():
                if not lines[index].lstrip().startswith("AI 初步判断："):
                    lines[index] = "AI 初步判断：" + lines[index].lstrip()
                break
        result = "\n".join(lines)

    note = (
        "## 自动一致性校验\n\n"
        "> 系统已将候选来源状态、检索边界和缺失字段改为确定性展示，并对过度相关性、现行有效、"
        "符合条件、特定资质或材料要求等未经原文支持的表述进行保守校正。候选页面仍须人工打开原文核验。"
    )
    if "## 自动一致性校验" not in result:
        result = f"{result.rstrip()}\n\n{note}"
    return result.strip()


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
        port = f":{parsed.port}" if parsed.port and parsed.port not in {80, 443} else ""
        return urlunparse(parsed._replace(scheme="https", netloc=host + port))
    if parsed.scheme == "http" and any(
        host == suffix or host.endswith("." + suffix)
        for suffix in ("gov.cn", "gd.gov.cn", "gz.gov.cn")
    ):
        return urlunparse(parsed._replace(scheme="https", netloc=host))
    return raw


def _query_text(profile: Mapping[str, Any] | None, demand: str) -> str:
    values = [demand]
    values.extend(_flatten_values(profile or {}))
    return _space(" ".join(values))


def _flatten_values(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        result: list[str] = []
        for item in value.values():
            result.extend(_flatten_values(item))
        return result
    if isinstance(value, (list, tuple, set)):
        result = []
        for item in value:
            result.extend(_flatten_values(item))
        return result
    return [_space(value)] if _space(value) else []


def _relevance_metrics(source: OfficialPolicySource, query: str) -> tuple[int, int, int]:
    title = source.title.casefold()
    excerpt = source.excerpt.casefold()
    folded_query = query.casefold()
    score = 0
    strong_matches = 0
    generic_title_matches = 0

    for term in _STRONG_TERMS:
        folded = term.casefold()
        if folded not in folded_query:
            continue
        if folded in title:
            score += 8
            strong_matches += 1
        elif folded in excerpt:
            score += 5
            strong_matches += 1

    for term in _GENERIC_TERMS:
        folded = term.casefold()
        if folded not in folded_query:
            continue
        if folded in title:
            score += 3
            generic_title_matches += 1
        elif folded in excerpt:
            score += 1

    return score, strong_matches, generic_title_matches


def _quality_score(source: OfficialPolicySource) -> int:
    score = 0
    if source.document_number:
        score += 2
    if source.issuer:
        score += 1
    if source.published_at:
        score += 1
    if source.effective_at or source.expires_at:
        score += 1
    if source.source_kind == "政策文件":
        score += 1
    if _has_substantive_excerpt(source.excerpt):
        score += 2
    return score


def _should_keep(
    source: OfficialPolicySource,
    query: str,
    metrics: tuple[int, int, int],
) -> tuple[bool, str]:
    text = _space(f"{source.title} {source.excerpt}")
    if not source.title or not source.official_url:
        return False, "weak_content"
    for audience, query_markers in _RESTRICTED_AUDIENCES.items():
        if audience in text and not any(marker in query for marker in query_markers):
            return False, "restricted_audience"
    if not _has_substantive_excerpt(source.excerpt):
        return False, "weak_content"
    for topic in _HARD_TOPIC_TERMS:
        if topic in text and topic not in query:
            return False, "unrelated_topic"
    if any(term in source.title for term in _FINANCE_TERMS) and not any(term in query for term in _FINANCE_TERMS):
        return False, "unrelated_topic"

    score, strong_matches, generic_title_matches = metrics
    if source.status in {"revoked", "expired", "suspended"}:
        return False, "inactive"
    if strong_matches >= 1 and score >= 5:
        return True, ""
    if generic_title_matches >= 2 and score >= 6:
        return True, ""
    return False, "low_relevance"


def _has_substantive_excerpt(excerpt: str) -> bool:
    value = _space(excerpt)
    if len(value) < 35:
        return False
    if value.lower().endswith(".pdf") and len(value) < 180:
        return False
    if ".pdf" in value.lower() and not re.search(r"[。；：]", value) and len(value) < 180:
        return False
    boilerplate = ("主办：", "承办：", "备案序号", "粤ICP备", "粤公网安备")
    if sum(marker in value for marker in boilerplate) >= 2:
        return False
    return True


def _retrieval_section(retrieval: OfficialPolicyRetrieval) -> str:
    catalogs = "<br>".join(_cell(value) for value in retrieval.searched_catalogs) or "未提供"
    warnings = "；".join(_cell(value) for value in retrieval.warnings) or "无额外告警"
    return "\n".join([
        "## 检索状态与范围",
        "",
        "| 项目 | 内容 |",
        "|---|---|",
        f"| 检索状态 | {_cell(_RETRIEVAL_STATUS_LABELS.get(retrieval.status, '状态待确认'))} |",
        f"| 检索时间 | {_cell(retrieval.retrieved_at)} |",
        f"| 官方目录 | {catalogs} |",
        f"| 保留候选数量 | {len(retrieval.sources)} 项 |",
        f"| 过滤与核验提示 | {warnings} |",
        "| 边界说明 | 页面来自允许名单政府域名并通过关键词与正文初筛；不代表适用区域、支持对象、政策效力或申报资格已确认。 |",
    ])


def _sources_section(retrieval: OfficialPolicyRetrieval) -> str:
    lines = ["## 官方候选来源", ""]
    if not retrieval.sources:
        lines.extend([
            "> 本次未保留可核验的直接相关官方候选来源。不得输出具体政策名称、申报资格、补贴金额或截止日期。",
            "",
            "建议改用更具体的检索词，并前往对应主管部门官网或政务服务窗口人工查询。",
        ])
        return "\n".join(lines)

    lines.extend([
        "| 引用编号 | 政策名称 | 文件类型 | 发布机关 | 文号 | 发布日期 | 页面解析日期 | 系统初判状态 | HTTPS 官方链接 |",
        "|---|---|---|---|---|---|---|---|---|",
    ])
    for source in retrieval.sources:
        parsed_dates = "；".join(
            part for part in (
                f"实施 {source.effective_at}" if source.effective_at else "",
                f"截至 {source.expires_at}" if source.expires_at else "",
            ) if part
        ) or "待打开原文核验"
        lines.append(
            "| {citation} | {title} | {kind} | {issuer} | {number} | {published} | {dates} | {status} | [打开官方原文]({url}) |".format(
                citation=_cell(source.citation_id),
                title=_cell(source.title),
                kind=_cell(source.source_kind),
                issuer=_cell(source.issuer or "待打开原文核验"),
                number=_cell(source.document_number or "待打开原文核验"),
                published=_cell(source.published_at or "待打开原文核验"),
                dates=_cell(parsed_dates),
                status=_cell(_STATUS_LABELS.get(source.status, "状态待人工核验")),
                url=source.official_url,
            )
        )
    return "\n".join(lines)


def _replace_section(content: str, title: str, replacement: str) -> str:
    pattern = re.compile(
        rf"(?ms)^##\s+{re.escape(title)}\s*\n.*?(?=^##\s+|\Z)"
    )
    if pattern.search(content):
        return pattern.sub(replacement.rstrip() + "\n\n", content, count=1).strip()
    return f"{content.rstrip()}\n\n{replacement.strip()}".strip()


def _cell(value: object) -> str:
    return str(value or "").replace("|", "｜").replace("\n", " ").strip()


def _space(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
