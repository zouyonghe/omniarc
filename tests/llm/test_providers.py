from __future__ import annotations

import httpx
import pytest

from omniarc.llm.client import LLMClient
from omniarc.llm.providers.anthropic import AnthropicProvider
from omniarc.llm.providers.base import LLMProvider
from omniarc.llm.providers.openai import OpenAIProvider
from omniarc.llm.providers.openai_compatible import OpenAICompatibleProvider
from omniarc.llm.types import (
    ConfigurationError,
    LLMConfig,
    LLMEndpointConfig,
    LLMRequest,
    LLMResponse,
    LLMRoleConfig,
    ProviderError,
)


@pytest.mark.asyncio
async def test_llm_client_selects_highest_priority_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = LLMConfig(
        endpoints=[
            LLMEndpointConfig(
                name="backup",
                provider="openai_compatible",
                base_url="https://backup.example.com/v1",
                api_key="backup-key",
                model="gpt-4o-mini",
                priority=2,
            ),
            LLMEndpointConfig(
                name="disabled",
                provider="openai_compatible",
                base_url="https://disabled.example.com/v1",
                api_key="disabled-key",
                model="gpt-4o-mini",
                priority=0,
                enabled=False,
            ),
            LLMEndpointConfig(
                name="primary",
                provider="openai_compatible",
                base_url="https://primary.example.com/v1",
                api_key="primary-key",
                model="gpt-4o",
                priority=1,
            ),
        ],
        roles={"planner": LLMRoleConfig(endpoint="primary")},
    )

    calls: list[str] = []

    async def fake_complete(
        self, endpoint: LLMEndpointConfig, request: LLMRequest
    ) -> LLMResponse:
        calls.append(endpoint.name)
        return LLMResponse(
            content="ok",
            provider=endpoint.provider,
            model=endpoint.model,
            metadata={"endpoint": endpoint.name},
        )

    monkeypatch.setattr(OpenAICompatibleProvider, "complete", fake_complete)

    client = LLMClient(config)
    response = await client.complete(
        LLMRequest(role="planner", prompt="Plan this task")
    )

    assert calls == ["primary"]
    assert response.metadata["endpoint"] == "primary"


@pytest.mark.asyncio
async def test_openai_compatible_provider_builds_expected_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    endpoint = LLMEndpointConfig(
        name="primary",
        provider="openai_compatible",
        base_url="https://api.openai.com/v1",
        api_key="openai-key",
        model="gpt-4o",
        priority=1,
    )
    provider = OpenAICompatibleProvider()
    captured: dict[str, object] = {}

    async def fake_post_json(self, *, endpoint, path, headers, payload):
        captured["endpoint"] = endpoint.name
        captured["path"] = path
        captured["headers"] = headers
        captured["payload"] = payload
        return {"choices": [{"message": {"content": "planned"}}]}

    monkeypatch.setattr(OpenAICompatibleProvider, "_post_json", fake_post_json)

    response = await provider.complete(
        endpoint,
        LLMRequest(
            role="planner",
            prompt="Plan this task",
            system_prompt="You are the planner.",
        ),
    )

    assert captured["path"] == "/chat/completions"
    assert captured["headers"] == {
        "Authorization": "Bearer openai-key",
        "Content-Type": "application/json",
    }
    assert captured["payload"] == {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are the planner."},
            {"role": "user", "content": "Plan this task"},
        ],
        "temperature": 0,
        "max_tokens": 1024,
    }
    assert response.content == "planned"


@pytest.mark.asyncio
async def test_anthropic_provider_builds_expected_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    endpoint = LLMEndpointConfig(
        name="claude",
        provider="anthropic",
        base_url="https://api.anthropic.com",
        api_key="anthropic-key",
        model="claude-3-5-sonnet",
        priority=1,
    )
    provider = AnthropicProvider()
    captured: dict[str, object] = {}

    async def fake_post_json(self, *, endpoint, path, headers, payload):
        captured["endpoint"] = endpoint.name
        captured["path"] = path
        captured["headers"] = headers
        captured["payload"] = payload
        return {"content": [{"type": "text", "text": "verified"}]}

    monkeypatch.setattr(AnthropicProvider, "_post_json", fake_post_json)

    response = await provider.complete(
        endpoint,
        LLMRequest(
            role="verifier",
            prompt="Verify the page",
            system_prompt="You are the verifier.",
        ),
    )

    assert captured["path"] == "/messages"
    assert captured["headers"] == {
        "x-api-key": "anthropic-key",
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    assert captured["payload"] == {
        "model": "claude-3-5-sonnet",
        "system": "You are the verifier.",
        "messages": [{"role": "user", "content": "Verify the page"}],
        "max_tokens": 1024,
        "temperature": 0,
    }
    assert response.content == "verified"


@pytest.mark.asyncio
async def test_base_provider_preserves_base_url_path_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    endpoint = LLMEndpointConfig(
        name="primary",
        provider="openai_compatible",
        base_url="https://api.openai.com/v1",
        api_key="openai-key",
        model="gpt-4o",
        priority=1,
    )
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"ok": True}

    class FakeAsyncClient:
        def __init__(self, *, timeout: int) -> None:
            captured["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, *, headers: dict, json: dict):
            captured["url"] = url
            captured["headers"] = headers
            captured["payload"] = json
            return FakeResponse()

    monkeypatch.setattr("omniarc.llm.providers.base.httpx.AsyncClient", FakeAsyncClient)

    class DummyProvider(LLMProvider):
        async def complete(self, endpoint, request):
            raise NotImplementedError

    provider = DummyProvider()
    response = await provider._post_json(
        endpoint=endpoint,
        path="/chat/completions",
        headers={"Authorization": "Bearer openai-key"},
        payload={"model": "gpt-4o"},
    )

    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert response == {"ok": True}


@pytest.mark.asyncio
async def test_base_provider_wraps_non_json_response_as_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    endpoint = LLMEndpointConfig(
        name="primary",
        provider="openai_compatible",
        base_url="https://api.openai.com/v1",
        api_key="openai-key",
        model="gpt-4o",
        priority=1,
    )

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            raise ValueError("not json")

    class FakeAsyncClient:
        def __init__(self, *, timeout: int) -> None:
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, *, headers: dict, json: dict):
            return FakeResponse()

    monkeypatch.setattr("omniarc.llm.providers.base.httpx.AsyncClient", FakeAsyncClient)

    class DummyProvider(LLMProvider):
        async def complete(self, endpoint, request):
            raise NotImplementedError

    provider = DummyProvider()

    with pytest.raises(ProviderError, match="non-json response"):
        await provider._post_json(
            endpoint=endpoint,
            path="/chat/completions",
            headers={"Authorization": "Bearer openai-key"},
            payload={"model": "gpt-4o"},
        )


@pytest.mark.asyncio
async def test_base_provider_wraps_transport_errors_as_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    endpoint = LLMEndpointConfig(
        name="primary",
        provider="openai_compatible",
        base_url="https://api.openai.com/v1",
        api_key="openai-key",
        model="gpt-4o",
        priority=1,
    )

    class FakeAsyncClient:
        def __init__(self, *, timeout: int) -> None:
            return None

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def post(self, url: str, *, headers: dict, json: dict):
            raise httpx.ConnectError("network down")

    monkeypatch.setattr("omniarc.llm.providers.base.httpx.AsyncClient", FakeAsyncClient)

    class DummyProvider(LLMProvider):
        async def complete(self, endpoint, request):
            raise NotImplementedError

    provider = DummyProvider()

    with pytest.raises(ProviderError, match="transport error"):
        await provider._post_json(
            endpoint=endpoint,
            path="/chat/completions",
            headers={"Authorization": "Bearer openai-key"},
            payload={"model": "gpt-4o"},
        )


@pytest.mark.asyncio
async def test_llm_client_falls_back_to_next_endpoint_on_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = LLMConfig(
        endpoints=[
            LLMEndpointConfig(
                name="backup",
                provider="openai_compatible",
                base_url="https://backup.example.com/v1",
                api_key="backup-key",
                model="gpt-4o-mini",
                priority=2,
            ),
            LLMEndpointConfig(
                name="primary",
                provider="openai_compatible",
                base_url="https://primary.example.com/v1",
                api_key="primary-key",
                model="gpt-4o",
                priority=1,
            ),
        ],
        roles={"planner": LLMRoleConfig(endpoint="primary")},
    )

    calls: list[str] = []

    async def fake_complete(
        self, endpoint: LLMEndpointConfig, request: LLMRequest
    ) -> LLMResponse:
        calls.append(endpoint.name)
        if endpoint.name == "primary":
            raise ProviderError("primary failed")
        return LLMResponse(
            content="fallback ok",
            provider=endpoint.provider,
            model=endpoint.model,
            metadata={"endpoint": endpoint.name},
        )

    monkeypatch.setattr(OpenAICompatibleProvider, "complete", fake_complete)

    client = LLMClient(config)
    response = await client.complete(
        LLMRequest(role="planner", prompt="Plan this task")
    )

    assert calls == ["primary", "backup"]
    assert response.metadata["endpoint"] == "backup"


@pytest.mark.asyncio
async def test_llm_client_rejects_missing_role_endpoint_mapping() -> None:
    config = LLMConfig(
        endpoints=[
            LLMEndpointConfig(
                name="primary",
                provider="openai_compatible",
                base_url="https://primary.example.com/v1",
                api_key="primary-key",
                model="gpt-4o",
                priority=1,
            )
        ],
        roles={"planner": LLMRoleConfig(endpoint="missing")},
    )

    client = LLMClient(config)

    with pytest.raises(ConfigurationError, match="unknown endpoint"):
        await client.complete(LLMRequest(role="planner", prompt="Plan this task"))


@pytest.mark.asyncio
async def test_llm_client_rejects_when_no_enabled_endpoints_exist() -> None:
    config = LLMConfig(
        endpoints=[
            LLMEndpointConfig(
                name="disabled",
                provider="openai_compatible",
                base_url="https://disabled.example.com/v1",
                api_key="disabled-key",
                model="gpt-4o-mini",
                priority=1,
                enabled=False,
            )
        ],
        roles={},
    )

    client = LLMClient(config)

    with pytest.raises(ConfigurationError, match="no enabled llm endpoints"):
        await client.complete(LLMRequest(role="planner", prompt="Plan this task"))


@pytest.mark.asyncio
async def test_llm_client_falls_back_on_malformed_primary_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = LLMConfig(
        endpoints=[
            LLMEndpointConfig(
                name="primary",
                provider="openai_compatible",
                base_url="https://primary.example.com/v1",
                api_key="primary-key",
                model="gpt-4o",
                priority=1,
            ),
            LLMEndpointConfig(
                name="backup",
                provider="openai_compatible",
                base_url="https://backup.example.com/v1",
                api_key="backup-key",
                model="gpt-4o-mini",
                priority=2,
            ),
        ],
        roles={"planner": LLMRoleConfig(endpoint="primary")},
    )

    async def fake_post_json(self, *, endpoint, path, headers, payload):
        if endpoint.name == "primary":
            return {}
        return {"choices": [{"message": {"content": "fallback ok"}}]}

    monkeypatch.setattr(OpenAICompatibleProvider, "_post_json", fake_post_json)

    client = LLMClient(config)
    response = await client.complete(
        LLMRequest(role="planner", prompt="Plan this task")
    )

    assert response.content == "fallback ok"
    assert response.metadata["endpoint"] == "backup"


@pytest.mark.asyncio
async def test_llm_client_reports_attempted_endpoints_when_all_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = LLMConfig(
        endpoints=[
            LLMEndpointConfig(
                name="primary",
                provider="openai_compatible",
                base_url="https://primary.example.com/v1",
                api_key="primary-key",
                model="gpt-4o",
                priority=1,
            ),
            LLMEndpointConfig(
                name="backup",
                provider="openai_compatible",
                base_url="https://backup.example.com/v1",
                api_key="backup-key",
                model="gpt-4o-mini",
                priority=2,
            ),
        ],
        roles={},
    )

    async def fake_complete(
        self, endpoint: LLMEndpointConfig, request: LLMRequest
    ) -> LLMResponse:
        raise ProviderError(f"{endpoint.name} failed")

    monkeypatch.setattr(OpenAICompatibleProvider, "complete", fake_complete)

    client = LLMClient(config)

    with pytest.raises(ProviderError, match="primary"):
        await client.complete(LLMRequest(role="planner", prompt="Plan this task"))


@pytest.mark.asyncio
async def test_anthropic_provider_rejects_malformed_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    endpoint = LLMEndpointConfig(
        name="claude",
        provider="anthropic",
        base_url="https://api.anthropic.com",
        api_key="anthropic-key",
        model="claude-3-5-sonnet",
        priority=1,
    )
    provider = AnthropicProvider()

    async def fake_post_json(self, *, endpoint, path, headers, payload):
        return {}

    monkeypatch.setattr(AnthropicProvider, "_post_json", fake_post_json)

    with pytest.raises(ProviderError, match="malformed anthropic response"):
        await provider.complete(
            endpoint,
            LLMRequest(
                role="verifier",
                prompt="Verify the page",
                system_prompt="You are the verifier.",
            ),
        )


@pytest.mark.asyncio
async def test_openai_provider_uses_api_key_env_when_inline_key_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    endpoint = LLMEndpointConfig(
        name="primary",
        provider="openai_compatible",
        base_url="https://api.openai.com/v1",
        api_key=None,
        api_key_env="OPENAI_API_KEY",
        model="gpt-4o",
        priority=1,
    )
    provider = OpenAICompatibleProvider()
    captured: dict[str, object] = {}
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")

    async def fake_post_json(self, *, endpoint, path, headers, payload):
        captured["headers"] = headers
        return {"choices": [{"message": {"content": "planned"}}]}

    monkeypatch.setattr(OpenAICompatibleProvider, "_post_json", fake_post_json)

    response = await provider.complete(
        endpoint,
        LLMRequest(role="planner", prompt="Plan this task"),
    )

    assert captured["headers"] == {
        "Authorization": "Bearer env-openai-key",
        "Content-Type": "application/json",
    }
    assert response.content == "planned"


@pytest.mark.asyncio
async def test_openai_provider_builds_responses_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    endpoint = LLMEndpointConfig(
        name="primary",
        provider="openai",
        base_url="https://api.openai.com/v1",
        api_key="openai-key",
        model="gpt-5.4",
        priority=1,
    )
    provider = OpenAIProvider()
    captured: dict[str, object] = {}

    async def fake_post_json(self, *, endpoint, path, headers, payload):
        captured["path"] = path
        captured["headers"] = headers
        captured["payload"] = payload
        return {"output": [{"content": [{"type": "output_text", "text": "planned"}]}]}

    monkeypatch.setattr(OpenAIProvider, "_post_json", fake_post_json)

    response = await provider.complete(
        endpoint,
        LLMRequest(
            role="planner",
            prompt="Plan this task",
            system_prompt="You are the planner.",
        ),
    )

    assert captured["path"] == "/responses"
    assert captured["headers"] == {
        "Authorization": "Bearer openai-key",
        "Content-Type": "application/json",
    }
    assert captured["payload"] == {
        "model": "gpt-5.4",
        "instructions": "You are the planner.",
        "input": "Plan this task",
        "max_output_tokens": 1024,
    }
    assert response.content == "planned"


@pytest.mark.asyncio
async def test_openai_provider_falls_back_to_chat_completions_when_responses_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    endpoint = LLMEndpointConfig(
        name="primary",
        provider="openai",
        base_url="https://proxy.example.com/openai",
        api_key="openai-key",
        model="gpt-5.4",
        priority=1,
    )
    provider = OpenAIProvider()
    calls: list[str] = []

    async def fake_post_json(self, *, endpoint, path, headers, payload):
        calls.append(path)
        if path == "/responses":
            raise ProviderError("transport error from endpoint primary")
        return {"choices": [{"message": {"content": "fallback planned"}}]}

    monkeypatch.setattr(OpenAIProvider, "_post_json", fake_post_json)

    response = await provider.complete(
        endpoint,
        LLMRequest(role="planner", prompt="Plan this task"),
    )

    assert calls == ["/responses", "/chat/completions"]
    assert response.content == "fallback planned"
