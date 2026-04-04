from __future__ import annotations

import asyncio

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
    ProviderError,
)

PROVIDER_REGISTRY: dict[str, type[LLMProvider]] = {
    "openai": OpenAIProvider,
    "openai_compatible": OpenAICompatibleProvider,
    "anthropic": AnthropicProvider,
}


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def complete_sync(self, request: LLMRequest) -> LLMResponse:
        return asyncio.run(self.complete(request))

    def _provider_for(self, provider_name: str) -> LLMProvider:
        provider_class = PROVIDER_REGISTRY.get(provider_name)
        if provider_class is None:
            raise ConfigurationError(f"unsupported provider: {provider_name}")
        return provider_class()

    def _candidate_endpoints(self, request: LLMRequest) -> list[LLMEndpointConfig]:
        enabled_endpoints = [
            endpoint for endpoint in self.config.endpoints if endpoint.enabled
        ]
        enabled_endpoints.sort(key=lambda endpoint: endpoint.priority)
        role_endpoint_name = self.config.roles.get(request.role)
        if role_endpoint_name is None:
            return enabled_endpoints
        ordered = [
            endpoint
            for endpoint in enabled_endpoints
            if endpoint.name == role_endpoint_name.endpoint
        ]
        if not ordered:
            raise ConfigurationError(
                f"unknown endpoint '{role_endpoint_name.endpoint}' referenced by role '{request.role}'"
            )
        ordered.extend(
            endpoint
            for endpoint in enabled_endpoints
            if endpoint.name != role_endpoint_name.endpoint
        )
        return ordered

    async def complete(self, request: LLMRequest) -> LLMResponse:
        candidates = self._candidate_endpoints(request)
        if not candidates:
            raise ConfigurationError("no enabled llm endpoints configured")

        failures: list[str] = []
        for endpoint in candidates:
            provider = self._provider_for(endpoint.provider)
            try:
                return await provider.complete(endpoint, request)
            except ProviderError as exc:
                failures.append(f"{endpoint.name}: {exc}")
        raise ProviderError("all llm endpoints failed: " + "; ".join(failures))
