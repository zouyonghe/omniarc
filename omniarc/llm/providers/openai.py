from __future__ import annotations

from omniarc.llm.providers.base import LLMProvider
from omniarc.llm.types import LLMEndpointConfig, LLMRequest, LLMResponse, ProviderError


class OpenAIProvider(LLMProvider):
    async def _complete_responses(
        self, endpoint: LLMEndpointConfig, request: LLMRequest
    ) -> LLMResponse:
        api_key = self._api_key_for(endpoint)
        data = await self._post_json(
            endpoint=endpoint,
            path="/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            payload={
                "model": endpoint.model,
                "instructions": request.system_prompt or "",
                "input": request.prompt,
                "max_output_tokens": request.max_tokens,
            },
        )
        try:
            content = "".join(
                item.get("text", "")
                for block in data["output"]
                for item in block.get("content", [])
                if item.get("type") == "output_text"
            )
            if not content:
                raise ProviderError(
                    f"malformed openai response from endpoint {endpoint.name}"
                )
        except (KeyError, TypeError, AttributeError) as exc:
            raise ProviderError(
                f"malformed openai response from endpoint {endpoint.name}"
            ) from exc
        return LLMResponse(
            content=content,
            provider=endpoint.provider,
            model=endpoint.model,
            metadata={"endpoint": endpoint.name, "api": "responses"},
        )

    async def _complete_chat(
        self, endpoint: LLMEndpointConfig, request: LLMRequest
    ) -> LLMResponse:
        api_key = self._api_key_for(endpoint)
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})
        data = await self._post_json(
            endpoint=endpoint,
            path="/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            payload={
                "model": endpoint.model,
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            },
        )
        try:
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise ProviderError(
                    f"malformed openai chat response from endpoint {endpoint.name}"
                )
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(
                f"malformed openai chat response from endpoint {endpoint.name}"
            ) from exc
        return LLMResponse(
            content=content,
            provider=endpoint.provider,
            model=endpoint.model,
            metadata={"endpoint": endpoint.name, "api": "chat_completions"},
        )

    async def complete(
        self, endpoint: LLMEndpointConfig, request: LLMRequest
    ) -> LLMResponse:
        try:
            return await self._complete_responses(endpoint, request)
        except ProviderError:
            return await self._complete_chat(endpoint, request)
