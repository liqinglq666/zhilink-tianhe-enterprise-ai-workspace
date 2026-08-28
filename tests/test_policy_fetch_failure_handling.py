from __future__ import annotations

import pytest
import requests

from zhilian_tianhe_agent.policy_retrieval import OfficialPolicyRetriever

OFFICIAL_URL = "https://www.thnet.gov.cn/policy"


class _FakeResponse:
    def __init__(self, *, status_code: int = 200, stream_error: Exception | None = None) -> None:
        self.status_code = status_code
        self.headers = {"Content-Type": "text/html; charset=utf-8"}
        self.encoding = "utf-8"
        self.apparent_encoding = "utf-8"
        self.stream_error = stream_error
        self.closed = False

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(
                "500 Server Error for url: https://www.thnet.gov.cn/private?token=secret"
            )

    def iter_content(self, chunk_size: int):  # noqa: ARG002
        yield b"<html>"
        if self.stream_error is not None:
            raise self.stream_error
        yield b"</html>"

    def close(self) -> None:
        self.closed = True


class _FakeSession:
    def __init__(self, response: _FakeResponse) -> None:
        self.response = response

    def get(self, *args, **kwargs):  # noqa: ANN002, ANN003, ARG002
        return self.response


def _service() -> OfficialPolicyRetriever:
    return OfficialPolicyRetriever(
        catalog_urls=[OFFICIAL_URL],
        allowed_domain_suffixes=["thnet.gov.cn"],
    )


def test_http_error_always_closes_streamed_response() -> None:
    service = _service()
    response = _FakeResponse(status_code=500)
    service._session = _FakeSession(response)

    with pytest.raises(requests.HTTPError):
        service._fetch_url(OFFICIAL_URL)

    assert response.closed is True


def test_stream_read_error_always_closes_response() -> None:
    service = _service()
    response = _FakeResponse(
        stream_error=requests.ConnectionError("secret stream diagnostic token=abc")
    )
    service._session = _FakeSession(response)

    with pytest.raises(requests.ConnectionError):
        service._fetch_url(OFFICIAL_URL)

    assert response.closed is True


def test_network_diagnostics_are_not_exposed_in_user_visible_warnings() -> None:
    def failing_fetch(url: str) -> str:  # noqa: ARG001
        raise requests.ConnectionError(
            "secret resolver diagnostic https://internal.example/?token=abc"
        )

    service = OfficialPolicyRetriever(
        catalog_urls=[OFFICIAL_URL],
        allowed_domain_suffixes=["thnet.gov.cn"],
        fetcher=failing_fetch,
    )
    result = service.search({}, "政策", limit=1)

    warnings = "\n".join(result.warnings)
    assert "官方页面暂时无法读取，请稍后重试。" in warnings
    assert "secret" not in warnings
    assert "internal.example" not in warnings
    assert "token=abc" not in warnings


def test_controlled_policy_validation_message_remains_actionable() -> None:
    def bounded_fetch(url: str) -> str:  # noqa: ARG001
        raise ValueError("官方页面内容超过安全读取上限。")

    service = OfficialPolicyRetriever(
        catalog_urls=[OFFICIAL_URL],
        allowed_domain_suffixes=["thnet.gov.cn"],
        fetcher=bounded_fetch,
    )
    result = service.search({}, "政策", limit=1)

    assert any("官方页面内容超过安全读取上限。" in warning for warning in result.warnings)
