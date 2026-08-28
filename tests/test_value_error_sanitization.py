from __future__ import annotations

import asyncio
import json

from backend.main import value_error_handler


def test_unexpected_value_error_is_not_exposed_to_client() -> None:
    response = asyncio.run(
        value_error_handler(
            None,  # handler does not inspect the request
            ValueError("secret internal parser detail: line 17 column 3"),
        )
    )

    assert response.status_code == 500
    payload = json.loads(response.body)
    assert payload == {
        "detail": "服务处理过程中发生异常，请稍后重试。",
        "code": "INTERNAL_VALUE_ERROR",
        "retryable": True,
    }
    assert "secret" not in response.body.decode("utf-8")
    assert "line 17" not in response.body.decode("utf-8")
