from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ConfigurationError(ValueError):
    pass


class ProviderError(RuntimeError):
    pass


class LLMModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LLMEndpointConfig(LLMModel):
    name: str
    provider: Literal["openai", "openai_compatible", "anthropic"]
    base_url: str
    model: str
    api_key: str | None = None
    api_key_env: str | None = None
    enabled: bool = True
    priority: int = 100
    timeout: int = 60


class LLMRoleConfig(LLMModel):
    endpoint: str


class LLMConfig(LLMModel):
    endpoints: list[LLMEndpointConfig] = Field(default_factory=list)
    roles: dict[str, LLMRoleConfig] = Field(default_factory=dict)


class LLMRequest(LLMModel):
    role: str
    prompt: str
    system_prompt: str | None = None
    max_tokens: int = 1024
    temperature: int | float = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(LLMModel):
    content: str
    provider: str
    model: str
    metadata: dict[str, Any] = Field(default_factory=dict)
