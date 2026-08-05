from __future__ import annotations

import pytest

from backend.schemas import DefaultsResponse
from zhilian_tianhe_agent import llm_client
from zhilian_tianhe_agent.errors import ModelGatewayError
from zhilian_tianhe_agent.llm_client import LLMConfig, public_model_available, public_model_status


PUBLIC_ENV_NAMES = (
    "PUBLIC_MODEL_ENABLED",
    "PUBLIC_MODEL_API_KEY",
    "PUBLIC_MODEL_BASE_URL",
    "PUBLIC_MODEL_MODEL",
    "PUBLIC_MODEL_PROVIDER",
    "PUBLIC_MODEL_TEMPERATURE",
    "PUBLIC_MODEL_DAILY_REQUEST_LIMIT",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "ALLOW_USER_API_OVERRIDE",
)


def clear_public_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in PUBLIC_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def enable_public_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_MODEL_ENABLED", "true")
    monkeypatch.setenv("PUBLIC_MODEL_API_KEY", "server-secret-key")
    monkeypatch.setenv("PUBLIC_MODEL_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setenv("PUBLIC_MODEL_MODEL", "qwen-plus")


def test_blank_client_config_remains_disabled_without_server_key(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_public_env(monkeypatch)
    config = LLMConfig(api_key="", base_url="https://client.example/v1", model="client-model")
    assert config.source == "unconfigured"
    assert config.api_key == ""
    assert not public_model_available()


def test_public_key_requires_explicit_enablement(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_public_env(monkeypatch)
    monkeypatch.setenv("PUBLIC_MODEL_API_KEY", "server-secret-key")
    monkeypatch.setenv("PUBLIC_MODEL_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setenv("PUBLIC_MODEL_MODEL", "qwen-plus")

    config = LLMConfig(api_key="", base_url="https://client.example/v1", model="client-model")
    assert config.source == "unconfigured"
    assert config.api_key == ""
    assert not public_model_available()


def test_legacy_openai_key_is_not_exposed_as_public_model(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_public_env(monkeypatch)
    monkeypatch.setenv("PUBLIC_MODEL_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "legacy-private-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setenv("OPENAI_MODEL", "qwen-plus")

    config = LLMConfig(api_key="", base_url="https://client.example/v1", model="client-model")
    assert config.source == "unconfigured"
    assert config.api_key == ""
    assert not public_model_available()


def test_server_key_uses_only_server_controlled_gateway_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_public_env(monkeypatch)
    enable_public_model(monkeypatch)
    monkeypatch.setenv("PUBLIC_MODEL_TEMPERATURE", "0.2")

    config = LLMConfig(
        api_key="",
        base_url="https://attacker.example/v1",
        model="attacker-model",
        temperature=0.9,
    )

    assert config.source == "server"
    assert config.api_key == "server-secret-key"
    assert config.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert config.model == "qwen-plus"
    assert config.temperature == 0.2
    assert "server-secret-key" not in repr(config)
    assert public_model_available()


def test_public_status_contains_no_key_or_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_public_env(monkeypatch)
    enable_public_model(monkeypatch)
    monkeypatch.setenv("PUBLIC_MODEL_PROVIDER", "阿里云百炼 DashScope")

    status = public_model_status()
    assert status == {
        "available": True,
        "provider": "阿里云百炼 DashScope",
        "model": "qwen-plus",
        "user_override_allowed": True,
    }
    serialized = str(status)
    assert "server-secret-key" not in serialized
    assert "dashscope.aliyuncs.com" not in serialized

    defaults = DefaultsResponse(provider_presets={}, modules={}, disclaimer="")
    assert defaults.public_model.available is True
    assert defaults.public_model.model == "qwen-plus"


def test_user_key_overrides_public_model_only_when_explicitly_supplied(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_public_env(monkeypatch)
    enable_public_model(monkeypatch)
    monkeypatch.setenv("ALLOW_USER_API_OVERRIDE", "true")

    config = LLMConfig(
        api_key="user-owned-key",
        base_url="https://api.example.com/v1",
        model="other-compatible-model",
        temperature=0.6,
    )

    assert config.source == "user"
    assert config.api_key == "user-owned-key"
    assert config.base_url == "https://api.example.com/v1"
    assert config.model == "other-compatible-model"
    assert config.temperature == 0.6


def test_user_override_can_be_disabled_by_deployment(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_public_env(monkeypatch)
    enable_public_model(monkeypatch)
    monkeypatch.setenv("ALLOW_USER_API_OVERRIDE", "false")

    with pytest.raises(ModelGatewayError) as exc_info:
        LLMConfig(api_key="user-owned-key", base_url="https://api.example.com/v1", model="model")

    assert exc_info.value.code == "MODEL_CONFIG_INVALID"


def test_public_quota_fuse_prompts_for_user_api(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_public_env(monkeypatch)
    monkeypatch.setenv("PUBLIC_MODEL_DAILY_REQUEST_LIMIT", "1")
    monkeypatch.setattr(llm_client, "_PUBLIC_USAGE_DAY", "")
    monkeypatch.setattr(llm_client, "_PUBLIC_USAGE_COUNT", 0)

    llm_client._consume_public_model_quota()
    with pytest.raises(ModelGatewayError) as exc_info:
        llm_client._consume_public_model_quota()

    assert exc_info.value.code == "PUBLIC_MODEL_QUOTA_EXHAUSTED"
    assert "自己的 API Key" in exc_info.value.user_message


def test_frontend_checks_public_mode_without_embedding_secret() -> None:
    source = open("frontend/assets/ui-redesign-live-fixes.js", encoding="utf-8").read()
    assert 'fetch("/api/defaults"' in source
    assert "publicAwareRequireApiConfig" in source
    assert "公共 Key 永远不会发送到用户指定的地址" in source
    assert "PUBLIC_MODEL_API_KEY" not in source
    assert "server-secret-key" not in source
