from __future__ import annotations

from abc import ABC, abstractmethod
import os
from typing import Any

import httpx

from omniarc.llm.types import (
    ConfigurationError,
    LLMEndpointConfig,
    LLMRequest,
    LLMResponse,
    ProviderError,
)


class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self, endpoint: LLMEndpointConfig, request: LLMRequest
    ) -> LLMResponse:
        raise NotImplementedError

    async def _post_json(
        self,
        *,
        endpoint: LLMEndpointConfig,
        path: str,
        headers: dict[str, str],
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        url = endpoint.base_url.rstrip("/") + "/" + path.lstrip("/")
        async with httpx.AsyncClient(timeout=endpoint.timeout) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise ProviderError(
                    f"transport error from endpoint {endpoint.name}"
                ) from exc
            try:
                return response.json()
            except ValueError as exc:
                raise ProviderError(
                    f"non-json response from endpoint {endpoint.name}"
                ) from exc

    def _api_key_for(self, endpoint: LLMEndpointConfig) -> str:
        api_key = endpoint.api_key
        if not api_key and endpoint.api_key_env:
            api_key = os.environ.get(endpoint.api_key_env)
        if not api_key:
            raise ConfigurationError(f"missing api key for endpoint: {endpoint.name}")
        return api_key
