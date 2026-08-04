# -*- coding: utf-8 -*-
"""HTTP security policy and CORS configuration helpers."""

from __future__ import annotations

from urllib.parse import urlparse

from starlette.responses import Response

DEFAULT_CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "object-src 'none'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self' data:",
        "connect-src 'self'",
        "media-src 'self'",
        "manifest-src 'self'",
    ]
)

DEFAULT_PERMISSIONS_POLICY = ", ".join(
    [
        "accelerometer=()",
        "camera=()",
        "geolocation=()",
        "gyroscope=()",
        "magnetometer=()",
        "microphone=()",
        "payment=()",
        "usb=()",
    ]
)


def parse_cors_origins(raw: str, *, allow_wildcard: bool = False) -> list[str]:
    """Parse and validate a comma-separated CORS origin allowlist."""

    values = [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]
    if not values:
        return []

    if "*" in values:
        if len(values) != 1:
            raise RuntimeError("CORS 通配符不能与具体域名同时配置。")
        if not allow_wildcard:
            raise RuntimeError("默认禁止 CORS 通配符；如确有需要，请显式启用 ALLOW_WILDCARD_CORS。")
        return ["*"]

    origins: list[str] = []
    for value in values:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError(f"CORS 来源格式不合法：{value}")
        if parsed.username or parsed.password:
            raise RuntimeError(f"CORS 来源不能包含账号或密码：{value}")
        if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
            raise RuntimeError(f"CORS 来源只能包含协议、域名和端口：{value}")
        if value not in origins:
            origins.append(value)
    return origins


def apply_security_headers(
    response: Response,
    *,
    path: str,
    content_security_policy: str = DEFAULT_CONTENT_SECURITY_POLICY,
    permissions_policy: str = DEFAULT_PERMISSIONS_POLICY,
    enable_hsts: bool = False,
    hsts_max_age: int = 31536000,
) -> Response:
    """Apply browser hardening headers without overwriting endpoint-specific headers."""

    headers = response.headers
    headers.setdefault("Content-Security-Policy", content_security_policy)
    headers.setdefault("X-Content-Type-Options", "nosniff")
    headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    headers.setdefault("Permissions-Policy", permissions_policy)
    headers.setdefault("X-Frame-Options", "DENY")
    headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
    headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")

    if enable_hsts:
        headers.setdefault(
            "Strict-Transport-Security",
            f"max-age={max(0, hsts_max_age)}; includeSubDomains",
        )

    if path == "/" or path.startswith("/api/"):
        headers.setdefault("Cache-Control", "no-store")
        headers.setdefault("Pragma", "no-cache")
    elif path.startswith("/assets/"):
        headers.setdefault("Cache-Control", "public, max-age=3600, must-revalidate")

    return response
