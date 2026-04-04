from __future__ import annotations

from omniarc.llm.providers.base import LLMProvider
from omniarc.llm.types import LLMEndpointConfig, LLMRequest, LLMResponse, ProviderError


class AnthropicProvider(LLMProvider):
    async def complete(
        self, endpoint: LLMEndpointConfig, request: LLMRequest
    ) -> LLMResponse:
        payload = {
            "model": endpoint.model,
            "system": request.system_prompt or "",
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        api_key = self._api_key_for(endpoint)
        data = await self._post_json(
            endpoint=endpoint,
            path="/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            payload=payload,
        )
        try:
            blocks = data["content"]
            content = "".join(
                block.get("text", "") for block in blocks if block.get("type") == "text"
            )
            if not content:
                raise ProviderError(
                    f"malformed anthropic response from endpoint {endpoint.name}"
                )
        except (AttributeError, KeyError, TypeError) as exc:
            raise ProviderError(
                f"malformed anthropic response from endpoint {endpoint.name}"
            ) from exc
        return LLMResponse(
            content=content,
            provider=endpoint.provider,
            model=endpoint.model,
            metadata={"endpoint": endpoint.name},
        )
