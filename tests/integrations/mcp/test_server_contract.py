import pytest

from omniarc.llm.types import LLMResponse
from omniarc.integrations.mcp.server import list_tool_names, validate_task


def test_server_exposes_expected_tools() -> None:
    assert list_tool_names() == [
        "health_check",
        "get_runtime_info",
        "list_skills",
        "validate_task",
        "run_task",
        "resume_task",
        "get_task_status",
        "pause_task",
        "inspect_run",
        "replay_run",
        "cancel_task",
        "get_run_artifact",
    ]


def test_validate_task_rejects_unsupported_phrase() -> None:
    result = validate_task("Open Safari, go to YouTube, and search for asmr")

    assert result == {
        "valid": False,
        "error": "task is not supported by the current planner",
    }


def test_validate_task_rejects_unsupported_chained_safari_phrase() -> None:
    result = validate_task("Open Safari and go to YouTube and search for asmr")

    assert result == {
        "valid": False,
        "error": "task is not supported by the current planner",
    }


def test_validate_task_rejects_unsupported_then_search_phrase() -> None:
    result = validate_task("Open Safari and go to YouTube then search for asmr")

    assert result == {
        "valid": False,
        "error": "task is not supported by the current planner",
    }


def test_validate_task_accepts_supported_phrase() -> None:
    result = validate_task("Open Finder")

    assert result == {"valid": True, "error": None}


def test_validate_task_accepts_windows_task_when_runtime_is_windows() -> None:
    result = validate_task("Open Notepad", runtime="windows")

    assert result == {"valid": True, "error": None}


def test_validate_task_accepts_unsupported_phrase_with_llm_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakePlanner:
        def plan_sync(self, task):
            return {
                "status": "supported",
                "source": "llm",
                "steps": [{"kind": "open_app", "params": {"name": "Safari"}}],
            }

    monkeypatch.setattr(
        "omniarc.integrations.mcp.server._build_planner",
        lambda runtime=None, llm_config_path=None, llm_profile=None: FakePlanner(),
    )

    result = validate_task(
        "Open Safari, go to YouTube, and search for asmr",
        runtime="macos",
        llm_config_path="/tmp/llm_endpoints.json",
        llm_profile="fast-verified",
    )

    assert result == {"valid": True, "error": None}


def test_validate_task_defaults_to_fast_verified_when_llm_config_is_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeLLMClient:
        def __init__(self, config) -> None:
            self.config = config

        def complete_sync(self, request):
            return LLMResponse(
                content='{"steps":[{"kind":"done","params":{}}]}',
                provider="openai_compatible",
                model="gpt-4o-mini",
            )

    monkeypatch.setattr(
        "omniarc.integrations.mcp.server.load_llm_config",
        lambda path: object(),
    )
    monkeypatch.setattr("omniarc.integrations.mcp.server.LLMClient", FakeLLMClient)

    result = validate_task(
        "Open Safari, go to YouTube, and search for asmr",
        runtime="macos",
        llm_config_path="/tmp/llm_endpoints.json",
    )

    assert result == {"valid": True, "error": None}


def test_validate_task_accepts_openai_provider_config_for_llm_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeLLMClient:
        def __init__(self, config) -> None:
            self.config = config

        def complete_sync(self, request):
            return LLMResponse(
                content='{"steps":[{"kind":"done","params":{}}]}',
                provider="openai",
                model="gpt-5.4",
            )

    class FakeConfig:
        class Endpoint:
            provider = "openai"

        endpoints = [Endpoint()]
        roles = {}

    monkeypatch.setattr(
        "omniarc.integrations.mcp.server.load_llm_config",
        lambda path: FakeConfig(),
    )
    monkeypatch.setattr("omniarc.integrations.mcp.server.LLMClient", FakeLLMClient)

    result = validate_task(
        "Open Safari, go to YouTube, and search for asmr",
        runtime="macos",
        llm_config_path="examples/llm_endpoints.json",
        llm_profile="fast-verified",
    )

    assert result == {"valid": True, "error": None}


def test_validate_task_returns_structured_error_for_bad_llm_config_path() -> None:
    result = validate_task(
        "Open Safari, go to YouTube, and search for asmr",
        runtime="macos",
        llm_config_path="/definitely/missing/llm_endpoints.json",
        llm_profile="fast-verified",
    )

    assert result["valid"] is False
    assert "could not read llm config" in result["error"]


def test_validate_task_rejects_unsupported_llm_profile() -> None:
    result = validate_task(
        "Open Finder",
        runtime="macos",
        llm_profile="slow-safe",
    )

    assert result == {"valid": False, "error": "unsupported llm profile: slow-safe"}
