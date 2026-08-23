from __future__ import annotations

import pytest
from starlette.responses import Response

from backend.security import apply_security_headers, parse_cors_origins


def test_parse_cors_origins_defaults_to_disabled():
    assert parse_cors_origins("") == []


def test_parse_cors_origins_validates_and_deduplicates():
    assert parse_cors_origins(
        "https://example.com, https://example.com/, http://localhost:8000"
    ) == ["https://example.com", "http://localhost:8000"]


def test_parse_cors_origins_rejects_wildcard_by_default():
    with pytest.raises(RuntimeError, match="通配符"):
        parse_cors_origins("*")


def test_parse_cors_origins_rejects_paths():
    with pytest.raises(RuntimeError, match="协议、域名和端口"):
        parse_cors_origins("https://example.com/app")


def test_apply_security_headers_to_api_response():
    response = apply_security_headers(Response("ok"), path="/api/defaults")

    assert response.headers["content-security-policy"].startswith("default-src 'self'")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"
    assert "strict-transport-security" not in response.headers


def test_apply_security_headers_can_enable_hsts():
    response = apply_security_headers(
        Response("ok"),
        path="/",
        enable_hsts=True,
        hsts_max_age=86400,
    )

    assert response.headers["strict-transport-security"] == "max-age=86400; includeSubDomains"


def test_endpoint_cache_control_is_not_overwritten():
    response = Response("stream", headers={"Cache-Control": "no-cache, no-transform"})
    apply_security_headers(response, path="/api/meeting/stream")

    assert response.headers["cache-control"] == "no-cache, no-transform"
