import json
from pathlib import Path

import pytest

from omniarc.llm.config import load_llm_config
from omniarc.llm.types import ConfigurationError


def test_load_llm_config_resolves_env_keys_and_sorts_enabled_endpoints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")
    config_path = tmp_path / "llm_endpoints.json"
    config_path.write_text(
        json.dumps(
            {
                "endpoints": [
                    {
                        "name": "backup",
                        "provider": "openai_compatible",
                        "base_url": "https://backup.example.com/v1",
                        "api_key_env": "OPENAI_API_KEY",
                        "model": "gpt-4o-mini",
                        "priority": 2,
                        "enabled": True,
                        "timeout": 30,
                    },
                    {
                        "name": "disabled",
                        "provider": "anthropic",
                        "base_url": "https://api.anthropic.com",
                        "api_key": "skip-me",
                        "model": "claude-3-5-sonnet",
                        "priority": 0,
                        "enabled": False,
                        "timeout": 30,
                    },
                    {
                        "name": "primary",
                        "provider": "openai_compatible",
                        "base_url": "https://api.openai.com/v1",
                        "api_key": "inline-key",
                        "model": "gpt-4o",
                        "priority": 1,
                        "enabled": True,
                        "timeout": 60,
                    },
                ],
                "roles": {
                    "planner": {"endpoint": "primary"},
                    "verifier": {"endpoint": "backup"},
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_llm_config(config_path)

    assert [endpoint.name for endpoint in config.endpoints] == ["primary", "backup"]
    assert config.endpoints[0].api_key == "inline-key"
    assert config.endpoints[1].api_key == "env-openai-key"
    assert config.roles["planner"].endpoint == "primary"
    assert config.roles["verifier"].endpoint == "backup"


def test_load_llm_config_accepts_openai_provider_name(tmp_path: Path) -> None:
    config_path = tmp_path / "llm_endpoints.json"
    config_path.write_text(
        json.dumps(
            {
                "endpoints": [
                    {
                        "name": "primary",
                        "provider": "openai",
                        "base_url": "https://api.openai.com/v1",
                        "api_key": "inline-key",
                        "model": "gpt-5.4",
                        "priority": 1,
                        "enabled": True,
                        "timeout": 60,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    config = load_llm_config(config_path)

    assert config.endpoints[0].provider == "openai"


def test_load_llm_config_rejects_invalid_endpoint_definition(tmp_path: Path) -> None:
    config_path = tmp_path / "llm_endpoints.json"
    config_path.write_text(
        json.dumps(
            {
                "endpoints": [
                    {
                        "name": "broken",
                        "provider": "openai_compatible",
                        "base_url": "https://api.openai.com/v1",
                        "priority": 1,
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="invalid endpoint config"):
        load_llm_config(config_path)


def test_load_llm_config_rejects_unknown_provider_name(tmp_path: Path) -> None:
    config_path = tmp_path / "llm_endpoints.json"
    config_path.write_text(
        json.dumps(
            {
                "endpoints": [
                    {
                        "name": "broken-provider",
                        "provider": "openia_compatible",
                        "base_url": "https://api.openai.com/v1",
                        "api_key": "inline-key",
                        "model": "gpt-4o",
                        "priority": 1,
                        "enabled": True,
                        "timeout": 60,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="invalid endpoint config"):
        load_llm_config(config_path)


def test_load_llm_config_rejects_role_reference_to_unknown_endpoint(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "llm_endpoints.json"
    config_path.write_text(
        json.dumps(
            {
                "endpoints": [
                    {
                        "name": "primary",
                        "provider": "openai_compatible",
                        "base_url": "https://api.openai.com/v1",
                        "api_key": "inline-key",
                        "model": "gpt-4o",
                        "priority": 1,
                        "enabled": True,
                        "timeout": 60,
                    }
                ],
                "roles": {"planner": {"endpoint": "missing"}},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="unknown endpoint"):
        load_llm_config(config_path)


def test_load_llm_config_rejects_duplicate_enabled_endpoint_names(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "llm_endpoints.json"
    config_path.write_text(
        json.dumps(
            {
                "endpoints": [
                    {
                        "name": "primary",
                        "provider": "openai_compatible",
                        "base_url": "https://api.openai.com/v1",
                        "api_key": "key-1",
                        "model": "gpt-4o",
                        "priority": 1,
                        "enabled": True,
                        "timeout": 60,
                    },
                    {
                        "name": "primary",
                        "provider": "anthropic",
                        "base_url": "https://api.anthropic.com",
                        "api_key": "key-2",
                        "model": "claude-3-5-sonnet",
                        "priority": 2,
                        "enabled": True,
                        "timeout": 60,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="duplicate endpoint"):
        load_llm_config(config_path)


def test_load_llm_config_rejects_duplicate_names_even_if_one_is_disabled(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "llm_endpoints.json"
    config_path.write_text(
        json.dumps(
            {
                "endpoints": [
                    {
                        "name": "primary",
                        "provider": "openai_compatible",
                        "base_url": "https://api.openai.com/v1",
                        "api_key": "key-1",
                        "model": "gpt-4o",
                        "priority": 1,
                        "enabled": True,
                        "timeout": 60,
                    },
                    {
                        "name": "primary",
                        "provider": "anthropic",
                        "base_url": "https://api.anthropic.com",
                        "api_key": "key-2",
                        "model": "claude-3-5-sonnet",
                        "priority": 2,
                        "enabled": False,
                        "timeout": 60,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="duplicate endpoint"):
        load_llm_config(config_path)


def test_load_llm_config_rejects_enabled_endpoint_without_resolved_api_key(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "llm_endpoints.json"
    config_path.write_text(
        json.dumps(
            {
                "endpoints": [
                    {
                        "name": "primary",
                        "provider": "openai_compatible",
                        "base_url": "https://api.openai.com/v1",
                        "api_key_env": "MISSING_OPENAI_API_KEY",
                        "model": "gpt-4o",
                        "priority": 1,
                        "enabled": True,
                        "timeout": 60,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="missing api key"):
        load_llm_config(config_path)


def test_load_llm_config_rejects_invalid_top_level_shapes(tmp_path: Path) -> None:
    config_path = tmp_path / "llm_endpoints.json"
    config_path.write_text(
        json.dumps({"endpoints": {}, "roles": []}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="invalid config shape"):
        load_llm_config(config_path)


def test_load_llm_config_rejects_unknown_top_level_keys(tmp_path: Path) -> None:
    config_path = tmp_path / "llm_endpoints.json"
    config_path.write_text(
        json.dumps({"endpoints": [], "roles": {}, "extra": 1}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="invalid config shape"):
        load_llm_config(config_path)


def test_load_llm_config_rejects_non_object_endpoint_entries(tmp_path: Path) -> None:
    config_path = tmp_path / "llm_endpoints.json"
    config_path.write_text(
        json.dumps({"endpoints": ["not-an-object"]}),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationError, match="invalid endpoint config"):
        load_llm_config(config_path)


def test_load_llm_config_wraps_missing_file_and_invalid_json(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.json"
    bad_json_path = tmp_path / "bad.json"
    bad_json_path.write_text("{not json", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="could not read llm config"):
        load_llm_config(missing_path)
    with pytest.raises(ConfigurationError, match="could not read llm config"):
        load_llm_config(bad_json_path)
