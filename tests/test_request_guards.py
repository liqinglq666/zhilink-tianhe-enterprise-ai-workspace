from fastapi.testclient import TestClient

from backend.main import RATE_LIMITER, app
from backend.schemas import MAX_MEETING_CHARS

client = TestClient(app)


def test_schema_limit_is_enforced_before_model_call():
    RATE_LIMITER.reset()
    response = client.post(
        "/api/meeting",
        json={
            "config": {},
            "text": "x" * (MAX_MEETING_CHARS + 1),
            "profile_summary": "",
        },
    )

    assert response.status_code == 422
    assert response.headers["x-ratelimit-limit"]


def test_rate_limit_returns_retry_after_header():
    old_limit = RATE_LIMITER.limit
    old_window = RATE_LIMITER.window_seconds
    RATE_LIMITER.limit = 1
    RATE_LIMITER.window_seconds = 60
    RATE_LIMITER.reset()

    try:
        payload = {
            "config": {},
            "results": {"企业档案": "测试内容"},
            "use_ai_summary": False,
        }
        assert client.post("/api/report/txt", json=payload).status_code == 200

        blocked = client.post("/api/report/txt", json=payload)
        assert blocked.status_code == 429
        assert blocked.headers["retry-after"] == "60"
    finally:
        RATE_LIMITER.limit = old_limit
        RATE_LIMITER.window_seconds = old_window
        RATE_LIMITER.reset()
