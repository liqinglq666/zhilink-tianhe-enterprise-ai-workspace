# -*- coding: utf-8 -*-
"""Allowlisted HTTPS policy retrieval with bounded TTL caching and stable citations."""
from __future__ import annotations

import hashlib
import os
import re
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from typing import Any, Callable, Iterable, Literal, Mapping
from urllib.parse import urljoin, urlparse

import requests
from pydantic import BaseModel, ConfigDict, Field

DEFAULT_CATALOG_URLS = (
    "https://www.thnet.gov.cn/zjth/tzth/tzzc/thzc/",
    "https://www.thnet.gov.cn/zwgk/zcjd/",
)
DEFAULT_ALLOWED_DOMAIN_SUFFIXES = ("thnet.gov.cn", "gz.gov.cn", "gd.gov.cn", "gov.cn")
POLICY_LINK_WORDS = (
    "政策", "措施", "办法", "通知", "规划", "意见", "细则", "方案", "指引",
    "申报", "扶持", "奖励", "补贴", "资金", "人才", "企业", "产业", "公示",
)
COMMON_QUERY_WORDS = (
    "软件", "人工智能", "科技", "创新", "小微企业", "个体工商户", "商贸", "文旅",
    "金融", "工业", "人才", "创业", "招商", "数字化", "知识产权", "低空经济",
    "专精特新", "高新技术", "融资", "消费", "文化", "电竞", "绿色", "节能",
)
MAX_RESPONSE_BYTES = 1_500_000
MAX_DOCUMENT_TEXT = 120_000
MAX_EXCERPT_CHARS = 500


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


PolicyDocumentStatus = Literal["active", "expired", "revoked", "suspended", "unknown"]
RetrievalStatus = Literal["ok", "partial", "no_results", "unavailable", "disabled"]


class OfficialPolicySource(StrictModel):
    citation_id: str = Field(pattern=r"^POL-\d{3}$")
    title: str = Field(max_length=500)
    official_url: str = Field(max_length=2000)
    official_domain: str = Field(max_length=255)
    source_kind: str = Field(default="政策文件", max_length=100)
    issuer: str = Field(default="", max_length=500)
    document_number: str = Field(default="", max_length=200)
    published_at: str = Field(default="", max_length=30)
    effective_at: str = Field(default="", max_length=30)
    expires_at: str = Field(default="", max_length=30)
    status: PolicyDocumentStatus = "unknown"
    excerpt: str = Field(default="", max_length=MAX_EXCERPT_CHARS)
    content_sha256: str = Field(min_length=64, max_length=64)
    retrieved_at: str = Field(max_length=50)


class OfficialPolicyRetrieval(StrictModel):
    query: str = Field(default="", max_length=2000)
    status: RetrievalStatus
    retrieved_at: str = Field(max_length=50)
    searched_catalogs: list[str] = Field(default_factory=list, max_length=20)
    warnings: list[str] = Field(default_factory=list, max_length=30)
    sources: list[OfficialPolicySource] = Field(default_factory=list, max_length=20)

    def to_prompt_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def to_markdown(self) -> str:
        lines = [
            "## 官方政策来源与原文引用", "",
            f"> 检索状态：{self.status}；检索时间：{self.retrieved_at}。仅下列 allowlist 官方域名页面可作为政策来源。", "",
        ]
        if not self.sources:
            lines.extend([
                "- 本次未获得可验证的官方政策原文。结果只能作为政策方向准备建议，不能据此判断资格、金额、期限或申报成功率。",
                "- 请前往天河区人民政府、广州市人民政府或相应主管部门官网人工核验。",
            ])
        else:
            lines.extend([
                "| 引用编号 | 政策文件 | 发布机关 | 文号 | 日期与状态 | 官方原文 |",
                "|---|---|---|---|---|---|",
            ])
            for source in self.sources:
                dates = "；".join(item for item in (
                    f"发布 {source.published_at}" if source.published_at else "",
                    f"实施 {source.effective_at}" if source.effective_at else "",
                    f"失效 {source.expires_at}" if source.expires_at else "",
                    f"状态 {source.status}",
                ) if item)
                lines.append(
                    f"| {source.citation_id} | {_cell(source.title)} | {_cell(source.issuer or '未从页面稳定识别')} | "
                    f"{_cell(source.document_number or '未从页面稳定识别')} | {_cell(dates)} | [打开官方原文]({source.official_url}) |"
                )
            lines.extend(["", "### 官方原文摘录", ""])
            for source in self.sources:
                lines.append(f"- **[{source.citation_id}] {source.title}**：{source.excerpt or '未提取到稳定摘录，请打开官方原文核对。'}")
        if self.warnings:
            lines.extend(["", "### 检索告警", "", *(f"- {warning}" for warning in self.warnings)])
        lines.extend([
            "", "## 政策检索边界", "",
            "- 官方页面摘录只能证明页面在检索时包含相应文字，不代表企业自动符合申报条件。",
            "- 文件可能被修订、废止、暂缓实施或由后续申报指南补充；正式使用前必须打开官方原文再次核验。",
            "- 金额、期限、适用区域、申报窗口和材料要求必须逐项引用对应官方文件，不得由 AI 补全。",
        ])
        return "\n".join(lines).strip()


class _PageParser(HTMLParser):
    BLOCK_TAGS = {"p", "div", "li", "br", "h1", "h2", "h3", "h4", "tr", "td", "th", "section", "article"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self.text_parts: list[str] = []
        self._anchor_href = ""
        self._anchor_text: list[str] = []
        self._in_title = False
        self._in_h1 = False
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"}:
            self._ignored_depth += 1
            return
        if self._ignored_depth:
            return
        if tag == "a":
            self._anchor_href = dict(attrs).get("href") or ""
            self._anchor_text = []
        elif tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._in_h1 = True
        if tag in self.BLOCK_TAGS:
            self.text_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript", "svg"} and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if self._ignored_depth:
            return
        if tag == "a" and self._anchor_href:
            text = _space("".join(self._anchor_text))
            if text:
                self.links.append((self._anchor_href, text))
            self._anchor_href, self._anchor_text = "", []
        elif tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_h1 = False
        if tag in self.BLOCK_TAGS:
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        if self._anchor_href:
            self._anchor_text.append(data)
        if self._in_title:
            self.title_parts.append(data)
        if self._in_h1:
            self.h1_parts.append(data)
        self.text_parts.append(data)

    @property
    def title(self) -> str:
        return _space("".join(self.h1_parts)) or _space("".join(self.title_parts))

    @property
    def text(self) -> str:
        lines = [_space(line) for line in "".join(self.text_parts).splitlines()]
        return "\n".join(line for line in lines if line)[:MAX_DOCUMENT_TEXT]


class _CacheEntry:
    def __init__(self, expires_at: float, value: OfficialPolicyRetrieval) -> None:
        self.expires_at = expires_at
        self.value = value


class OfficialPolicyRetriever:
    def __init__(
        self,
        *,
        catalog_urls: Iterable[str] | None = None,
        allowed_domain_suffixes: Iterable[str] | None = None,
        fetcher: Callable[[str], str] | None = None,
    ) -> None:
        configured_catalogs = _env_csv("POLICY_CATALOG_URLS")
        configured_domains = _env_csv("POLICY_ALLOWED_DOMAINS")
        self.catalog_urls = tuple(catalog_urls or configured_catalogs or DEFAULT_CATALOG_URLS)
        self.allowed_domain_suffixes = tuple(
            item.lower().lstrip(".")
            for item in (allowed_domain_suffixes or configured_domains or DEFAULT_ALLOWED_DOMAIN_SUFFIXES)
            if item
        )
        self.fetcher = fetcher or self._fetch_url
        self.enabled = _env_bool("POLICY_RETRIEVAL_ENABLED", True)
        self.timeout = _env_float("POLICY_FETCH_TIMEOUT_SECONDS", 6.0, 2.0, 20.0)
        self.cache_ttl = _env_int("POLICY_CACHE_TTL_SECONDS", 900, 30, 86400)
        self.cache_max_entries = _env_int("POLICY_CACHE_MAX_ENTRIES", 256, 16, 4096)
        self.max_catalog_pages = _env_int("POLICY_MAX_CATALOG_PAGES", 4, 1, 10)
        self.max_results = _env_int("POLICY_MAX_RESULTS", 6, 1, 12)
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "ZhiLink-Tianhe-Policy-Retriever/1.0 (+official-source-verification)",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.8",
        })

    def _prune_cache(self, now: float) -> None:
        expired = [key for key, entry in self._cache.items() if entry.expires_at <= now]
        for key in expired:
            self._cache.pop(key, None)
        while len(self._cache) > self.cache_max_entries:
            self._cache.popitem(last=False)

    def search(self, profile: Mapping[str, Any] | None, demand: str = "", *, query: str = "", limit: int | None = None) -> OfficialPolicyRetrieval:
        retrieved_at = datetime.now(timezone.utc).isoformat()
        combined_query = _build_query(profile or {}, demand, query)
        if not self.enabled:
            return OfficialPolicyRetrieval(query=combined_query, status="disabled", retrieved_at=retrieved_at, warnings=["官方政策检索已由部署配置关闭。"])

        result_limit = max(1, min(int(limit or self.max_results), 12))
        cache_key = hashlib.sha256(
            (combined_query + "\n" + "\n".join(self.catalog_urls) + f"\nlimit={result_limit}").encode("utf-8")
        ).hexdigest()
        now = time.time()
        with self._lock:
            self._prune_cache(now)
            cached = self._cache.get(cache_key)
            if cached:
                self._cache.move_to_end(cache_key)
                return cached.value.model_copy(deep=True)

        warnings: list[str] = []
        candidates: dict[str, str] = {}
        searched_catalogs: list[str] = []
        catalog_failures = 0
        for start_url in self.catalog_urls:
            try:
                self._validate_url(start_url)
                queue, visited = [start_url], set()
                while queue and len(visited) < self.max_catalog_pages:
                    catalog_url = queue.pop(0)
                    if catalog_url in visited:
                        continue
                    visited.add(catalog_url)
                    parser = _parse(self.fetcher(catalog_url))
                    searched_catalogs.append(catalog_url)
                    for href, title in parser.links:
                        url = urljoin(catalog_url, href)
                        if not self._is_allowed_url(url):
                            continue
                        if _looks_like_pagination(title, url, start_url):
                            if url not in visited and url not in queue:
                                queue.append(url)
                        elif _looks_like_policy_link(title, url):
                            candidates.setdefault(url, title[:500])
            except Exception as exc:  # noqa: BLE001
                catalog_failures += 1
                warnings.append(f"官方目录读取失败：{_safe_error(exc)}")

        ranked = sorted(candidates.items(), key=lambda item: (_rank(item[1], combined_query), item[1]), reverse=True)
        candidate_limit = min(max(result_limit * 4, 12), 36)
        sources: list[OfficialPolicySource] = []
        failures = 0
        with ThreadPoolExecutor(max_workers=min(6, candidate_limit or 1)) as executor:
            future_map = {executor.submit(self._read_document, url, title, combined_query): url for url, title in ranked[:candidate_limit]}
            for future in as_completed(future_map):
                try:
                    source, score = future.result()
                    if source and score > 0:
                        sources.append(source)
                except Exception as exc:  # noqa: BLE001
                    failures += 1
                    if failures <= 3:
                        warnings.append(f"部分官方原文读取失败：{_safe_error(exc)}")

        sources.sort(key=lambda item: (_rank(item.title + " " + item.excerpt, combined_query), item.published_at, item.title), reverse=True)
        selected = [source.model_copy(update={"citation_id": f"POL-{index:03d}"}) for index, source in enumerate(sources[:result_limit], 1)]
        if selected:
            status: RetrievalStatus = "partial" if warnings else "ok"
        elif catalog_failures >= len(self.catalog_urls) and self.catalog_urls:
            status = "unavailable"
        else:
            status = "no_results"
            warnings.append("未在当前官方目录中找到与输入明显匹配的政策文件。")
        result = OfficialPolicyRetrieval(
            query=combined_query,
            status=status,
            retrieved_at=retrieved_at,
            searched_catalogs=list(dict.fromkeys(searched_catalogs))[:20],
            warnings=list(dict.fromkeys(warnings))[:30],
            sources=selected,
        )
        with self._lock:
            self._cache[cache_key] = _CacheEntry(time.time() + self.cache_ttl, result)
            self._cache.move_to_end(cache_key)
            self._prune_cache(time.time())
        return result.model_copy(deep=True)

    def _read_document(self, url: str, catalog_title: str, query: str) -> tuple[OfficialPolicySource | None, int]:
        parser = _parse(self.fetcher(url))
        text = parser.text
        title = _clean_title(parser.title or catalog_title)
        if not title or len(text) < 80:
            return None, 0
        score = _rank(title + " " + text[:5000], query)
        if score <= 0 and query:
            return None, score
        issuer = _match_metadata(text, ("发布机关", "发布单位", "来源"), 500)
        document_number = _match_document_number(text)
        published_at = _match_date(text, ("发布时间", "发布日期", "印发日期"))
        effective_at = _match_date(text, ("实施日期", "施行日期", "自"))
        expires_at = _match_date(text, ("失效日期", "有效期至", "有效期截止"))
        normalized = _space(text)
        domain = (urlparse(url).hostname or "").lower()
        return OfficialPolicySource(
            citation_id="POL-000",
            title=title,
            official_url=url,
            official_domain=domain,
            source_kind="政策解读" if "解读" in title or "zcjd" in url else "政策文件",
            issuer=issuer,
            document_number=document_number,
            published_at=published_at,
            effective_at=effective_at,
            expires_at=expires_at,
            status=_document_status(title, text, expires_at),
            excerpt=_select_excerpt(text, query, title),
            content_sha256=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
            retrieved_at=datetime.now(timezone.utc).isoformat(),
        ), score

    def _is_allowed_url(self, url: str) -> bool:
        try:
            self._validate_url(url)
            return True
        except ValueError:
            return False

    def _validate_url(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ValueError("政策来源 URL 必须使用 HTTPS。")
        if parsed.username or parsed.password:
            raise ValueError("政策来源 URL 不允许包含认证信息。")
        if parsed.port not in {None, 443}:
            raise ValueError("政策来源 URL 不允许使用非标准端口。")
        host = (parsed.hostname or "").lower().rstrip(".")
        if not host or not any(host == suffix or host.endswith("." + suffix) for suffix in self.allowed_domain_suffixes):
            raise ValueError("政策来源域名不在官方 allowlist。")

    def _fetch_url(self, url: str) -> str:
        current = url
        for _ in range(4):
            self._validate_url(current)
            response = self._session.get(current, timeout=(min(self.timeout, 5.0), self.timeout), allow_redirects=False, stream=True)
            try:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("Location", "")
                    if not location:
                        raise ValueError("官方页面重定向缺少目标地址。")
                    current = urljoin(current, location)
                    continue
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "").lower()
                if content_type and not any(item in content_type for item in ("text/html", "text/plain", "application/xhtml")):
                    raise ValueError("官方页面返回了不支持的内容类型。")
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_content(65536):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > MAX_RESPONSE_BYTES:
                        raise ValueError("官方页面内容超过安全读取上限。")
                    chunks.append(chunk)
                encoding = response.encoding or response.apparent_encoding or "utf-8"
                return b"".join(chunks).decode(encoding, errors="replace")
            finally:
                response.close()
        raise ValueError("官方页面重定向次数过多。")


_RETRIEVER: OfficialPolicyRetriever | None = None
_RETRIEVER_LOCK = threading.Lock()


def get_official_policy_retriever() -> OfficialPolicyRetriever:
    global _RETRIEVER
    with _RETRIEVER_LOCK:
        if _RETRIEVER is None:
            _RETRIEVER = OfficialPolicyRetriever()
        return _RETRIEVER


def reset_official_policy_retriever_for_tests() -> None:
    global _RETRIEVER
    with _RETRIEVER_LOCK:
        _RETRIEVER = None


def _parse(html: str) -> _PageParser:
    parser = _PageParser()
    parser.feed(html or "")
    parser.close()
    return parser


def _env_csv(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "").strip()
    return tuple(item.strip() for item in re.split(r"[;,\n]", raw) if item.strip()) if raw else ()


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    return default if not raw else raw in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)).strip())
    except ValueError:
        value = default
    return max(minimum, min(value, maximum))


def _env_float(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(os.getenv(name, str(default)).strip())
    except ValueError:
        value = default
    return max(minimum, min(value, maximum))


def _space(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _cell(value: object) -> str:
    return _space(value).replace("|", "\\|").replace("\n", " ")


def _clean_title(value: str) -> str:
    title = _space(value)
    for suffix in (" - 广州市人民政府门户网站", " - 广州市天河区人民政府门户网站", "_广州市人民政府门户网站"):
        if title.endswith(suffix):
            title = title[: -len(suffix)].strip()
    return title[:500]


def _looks_like_policy_link(title: str, url: str) -> bool:
    clean = _space(title)
    return len(clean) >= 8 and clean not in {"首页", "上一页", "下一页", "第一页", "最后一页"} and any(word in clean for word in POLICY_LINK_WORDS)


def _looks_like_pagination(title: str, url: str, start_url: str) -> bool:
    clean = _space(title)
    if clean in {"第一页", "上一页", "下一页", "最后一页"} or clean.isdigit():
        return True
    parsed, start = urlparse(url), urlparse(start_url)
    return parsed.hostname == start.hostname and "index_" in parsed.path and parsed.path.rsplit("/", 1)[0] == start.path.rstrip("/")


def _query_tokens(query: str) -> list[str]:
    normalized = _space(query)
    tokens = [word for word in COMMON_QUERY_WORDS if word in normalized]
    for item in re.findall(r"[A-Za-z0-9]{2,}|[\u4e00-\u9fff]{2,12}", normalized):
        if len(item) <= 6:
            tokens.append(item)
        elif re.fullmatch(r"[\u4e00-\u9fff]+", item):
            tokens.extend(item[index : index + 2] for index in range(min(len(item) - 1, 8)))
    return list(dict.fromkeys(token for token in tokens if token))[:40]


def _rank(text: str, query: str) -> int:
    haystack = _space(text).lower()
    tokens = _query_tokens(query)
    if not tokens:
        return sum(1 for word in POLICY_LINK_WORDS if word in haystack)
    score = sum(min(haystack.count(token.lower()), 5) * (4 if len(token) >= 4 else 2) for token in tokens)
    if "天河" in haystack:
        score += 3
    if any(word in haystack for word in ("废止", "暂缓实施", "失效")):
        score += 1
    return score


def _build_query(profile: Mapping[str, Any], demand: str, query: str) -> str:
    parts = [query, demand]
    parts.extend(_space(profile.get(key)) for key in ("industry", "location", "stage", "demands", "name") if _space(profile.get(key)))
    return _space(" ".join(part for part in parts if _space(part)))[:2000]


def _match_metadata(text: str, labels: Iterable[str], limit: int) -> str:
    for label in labels:
        match = re.search(rf"{re.escape(label)}\s*[：:]\s*([^\n]{{2,{limit}}})", text)
        if match:
            return _space(match.group(1))[:limit]
    return ""


def _match_document_number(text: str) -> str:
    labeled = re.search(r"(?:文\s*号|发文字号)\s*[：:]\s*([^\n]{2,100})", text)
    if labeled:
        return _space(labeled.group(1))[:200]
    generic = re.search(r"[\u4e00-\u9fff]{1,12}(?:规字|府办|府|办|函|发|公告)〔\d{4}〕\d+号", text)
    return generic.group(0)[:200] if generic else ""


def _normalize_date(raw: str) -> str:
    match = re.search(r"(20\d{2})[年./-](\d{1,2})[月./-](\d{1,2})日?", raw)
    if not match:
        return ""
    try:
        return date(*map(int, match.groups())).isoformat()
    except ValueError:
        return ""


def _match_date(text: str, labels: Iterable[str]) -> str:
    for label in labels:
        match = re.search(rf"{re.escape(label)}[^\d]{{0,12}}(20\d{{2}}[年./-]\d{{1,2}}[月./-]\d{{1,2}}日?)", text)
        if match:
            normalized = _normalize_date(match.group(1))
            if normalized:
                return normalized
    return ""


def _document_status(title: str, text: str, expires_at: str) -> PolicyDocumentStatus:
    head = _space(title + " " + text[:4000])
    if any(word in head for word in ("废止", "停止执行", "予以废止")):
        return "revoked"
    if any(word in head for word in ("暂缓实施", "暂停实施", "中止实施")):
        return "suspended"
    if expires_at:
        try:
            return "expired" if date.fromisoformat(expires_at) < datetime.now(timezone.utc).date() else "active"
        except ValueError:
            pass
    return "unknown"


def _select_excerpt(text: str, query: str, title: str) -> str:
    tokens = _query_tokens(query)
    chunks = [_space(item) for item in re.split(r"(?<=[。！？；])|\n+", text) if 20 <= len(_space(item)) <= 1200]
    scored: list[tuple[int, str]] = []
    for chunk in chunks:
        if chunk == title or chunk.startswith("您当前所在的位置") or ("人民政府门户网站" in chunk and len(chunk) < 120):
            continue
        score = sum((4 if len(token) >= 4 else 2) for token in tokens if token in chunk)
        if any(word in chunk for word in ("适用范围", "申报", "支持", "奖励", "补贴", "有效期", "实施日期")):
            score += 8
        scored.append((score, chunk))
    scored.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
    chosen = next((chunk for score, chunk in scored if score > 0), "") or next((chunk for _, chunk in scored if not chunk.startswith(("首页", "搜索热词"))), "")
    return chosen[:MAX_EXCERPT_CHARS]


def _safe_error(exc: Exception) -> str:
    if isinstance(exc, ValueError):
        return (_space(str(exc)) or "官方页面内容不符合安全读取要求。")[:180]
    return "官方页面暂时无法读取，请稍后重试。"
