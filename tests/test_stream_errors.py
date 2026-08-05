from backend.main import _stream_error_payload
from zhilian_tianhe_agent.errors import ModelGatewayError


def test_stream_error_payload_keeps_model_metadata():
    error = ModelGatewayError(
        code="MODEL_RATE_LIMITED",
        user_message="模型服务请求过于频繁。",
        status_code=429,
        retryable=True,
        retry_after=15,
    )

    assert _stream_error_payload(error) == {
        "type": "error",
        "error": "模型服务请求过于频繁。",
        "code": "MODEL_RATE_LIMITED",
        "retryable": True,
        "retry_after": 15,
    }


def test_stream_error_payload_hides_unknown_exception_detail():
    payload = _stream_error_payload(RuntimeError("secret internal detail"))

    assert payload["code"] == "STREAM_INTERNAL_ERROR"
    assert payload["retryable"] is True
    assert "secret" not in payload["error"]
