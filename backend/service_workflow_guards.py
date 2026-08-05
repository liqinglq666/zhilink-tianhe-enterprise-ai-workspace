# -*- coding: utf-8 -*-
"""Security and project-state guards for enterprise-service workflows."""
from __future__ import annotations

import re
from urllib.parse import urlparse
from sqlalchemy import select
from .auth_store import AccountStoreError, OrganizationProjectRecord, get_account_store
from .project_store import ProjectRecord

POLICY_RE = re.compile(r"\bPOL-\d{3}\b")
URL_RE = re.compile(r"\((https://[^\s)]+)\)")
GOV_SUFFIXES = ("gov.cn", "gd.gov.cn", "gz.gov.cn", "thnet.gov.cn")


def _clean(value: str, limit: int = 500) -> str:
    return " ".join(re.sub(r"^[\s>*#\-+\d.\[\]xX]+", "", value or "").split())[:limit]


def _safe_government_url(raw: str) -> str:
    try:
        parsed = urlparse(raw)
        host = (parsed.hostname or "").lower()
        trusted = any(host == suffix or host.endswith("." + suffix) for suffix in GOV_SUFFIXES)
        if parsed.scheme == "https" and trusted and not parsed.username and not parsed.password and parsed.port in (None, 443):
            return raw[:2000]
    except ValueError:
        pass
    return ""


def safe_official_references(markdown: str) -> list[dict[str, str]]:
    references: dict[str, dict[str, str]] = {}
    for line in (markdown or "").splitlines():
        ids = POLICY_RE.findall(line)
        if not ids:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        url_match = URL_RE.search(line)
        for citation_id in ids:
            item = references.setdefault(citation_id, {"citation_id": citation_id, "title": "", "official_url": ""})
            if len(cells) >= 2 and citation_id in cells[0]:
                item["title"] = _clean(cells[1])
            if url_match:
                item["official_url"] = _safe_government_url(url_match.group(1))
    return [references[key] for key in sorted(references)][:20]


def ensure_active_organization_project(organization_id: str, project_id: str) -> None:
    account = get_account_store()
    with account.sessions() as session:
        project = session.scalar(
            select(ProjectRecord)
            .join(OrganizationProjectRecord, OrganizationProjectRecord.project_id == ProjectRecord.id)
            .where(ProjectRecord.id == project_id, OrganizationProjectRecord.organization_id == organization_id)
        )
        if project is None:
            raise AccountStoreError(404, "WORKFLOW_PROJECT_NOT_FOUND", "项目不存在、未迁移到当前组织或无权访问。")
        if project.status != "active":
            raise AccountStoreError(409, "WORKFLOW_PROJECT_ARCHIVED", "已归档项目不能创建新的企业服务流程。")
