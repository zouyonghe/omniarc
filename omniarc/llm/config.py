from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import ValidationError

from omniarc.llm.types import (
    ConfigurationError,
    LLMConfig,
    LLMEndpointConfig,
    LLMRoleConfig,
)


def load_llm_config(config_path: Path | str) -> LLMConfig:
    path = Path(config_path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"could not read llm config: {path}") from exc
    if not isinstance(raw, dict):
        raise ConfigurationError(
            "invalid config shape: top-level JSON must be an object"
        )
    allowed_keys = {"endpoints", "roles"}
    unknown_keys = set(raw) - allowed_keys
    if unknown_keys:
        raise ConfigurationError(
            "invalid config shape: unknown top-level keys "
            + ", ".join(sorted(unknown_keys))
        )

    endpoints_raw = raw.get("endpoints", [])
    roles_raw = raw.get("roles", {})
    if not isinstance(endpoints_raw, list) or not isinstance(roles_raw, dict):
        raise ConfigurationError(
            "invalid config shape: endpoints must be a list and roles must be an object"
        )

    endpoints: list[LLMEndpointConfig] = []
    seen_endpoint_names: set[str] = set()
    for item in endpoints_raw:
        if not isinstance(item, dict):
            raise ConfigurationError(
                "invalid endpoint config: endpoint entry must be an object"
            )
        payload = dict(item)
        endpoint_name = payload.get("name")
        if isinstance(endpoint_name, str):
            if endpoint_name in seen_endpoint_names:
                raise ConfigurationError(f"duplicate endpoint name: {endpoint_name}")
            seen_endpoint_names.add(endpoint_name)
        if not payload.get("api_key") and payload.get("api_key_env"):
            payload["api_key"] = os.environ.get(str(payload["api_key_env"]))
        try:
            endpoint = LLMEndpointConfig.model_validate(payload)
        except ValidationError as exc:
            raise ConfigurationError(f"invalid endpoint config: {exc}") from exc
        if endpoint.enabled:
            if not endpoint.api_key:
                raise ConfigurationError(
                    f"missing api key for enabled endpoint: {endpoint.name}"
                )
            endpoints.append(endpoint)

    endpoints.sort(key=lambda endpoint: endpoint.priority)

    roles: dict[str, LLMRoleConfig] = {}
    known_endpoints = {endpoint.name for endpoint in endpoints}
    for role_name, role_payload in roles_raw.items():
        try:
            role = LLMRoleConfig.model_validate(role_payload)
        except ValidationError as exc:
            raise ConfigurationError(f"invalid role config: {exc}") from exc
        if role.endpoint not in known_endpoints:
            raise ConfigurationError(
                f"unknown endpoint '{role.endpoint}' referenced by role '{role_name}'"
            )
        roles[role_name] = role

    return LLMConfig(endpoints=endpoints, roles=roles)
