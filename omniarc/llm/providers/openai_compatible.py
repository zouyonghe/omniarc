from __future__ import annotations

from omniarc.llm.providers.base import LLMProvider
from omniarc.llm.types import LLMEndpointConfig, LLMRequest, LLMResponse, ProviderError


class OpenAICompatibleProvider(LLMProvider):
    async def complete(
        self, endpoint: LLMEndpointConfig, request: LLMRequest
    ) -> LLMResponse:
        messages = []
        api_key = self._api_key_for(endpoint)
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        payload = {
            "model": endpoint.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        data = await self._post_json(
            endpoint=endpoint,
            path="/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            payload=payload,
        )
        try:
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise ProviderError(
                    f"malformed openai-compatible response from endpoint {endpoint.name}"
                )
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(
                f"malformed openai-compatible response from endpoint {endpoint.name}"
            ) from exc
        return LLMResponse(
            content=content,
            provider=endpoint.provider,
            model=endpoint.model,
            metadata={"endpoint": endpoint.name},
        )
