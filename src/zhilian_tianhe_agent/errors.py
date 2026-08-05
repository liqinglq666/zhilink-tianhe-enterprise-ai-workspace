from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(eq=False)
class ModelGatewayError(RuntimeError):
    code: str
    user_message: str
    status_code: int = 502
    retryable: bool = False
    retry_after: int | None = None

    def __post_init__(self) -> None:
        RuntimeError.__init__(self, self.user_message)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "detail": self.user_message,
            "code": self.code,
            "retryable": self.retryable,
        }
        if self.retry_after is not None:
            payload["retry_after"] = self.retry_after
        return payload


def configuration_error(message: str) -> ModelGatewayError:
    return ModelGatewayError(
        code="MODEL_CONFIG_INVALID",
        user_message=message,
        status_code=400,
        retryable=False,
    )


def unavailable_error() -> ModelGatewayError:
    return ModelGatewayError(
        code="MODEL_UNAVAILABLE",
        user_message="模型服务暂时不可用，请稍后重试。",
        status_code=503,
        retryable=True,
    )
