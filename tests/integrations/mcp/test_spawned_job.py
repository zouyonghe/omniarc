import time
import json
from pathlib import Path

import pytest

from omniarc.integrations.mcp.server import get_task_status, run_task


def test_run_task_spawns_background_dry_run(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    result = run_task(
        task="Open Finder",
        max_steps=3,
        dry_run=True,
        artifacts_dir=str(artifacts_dir),
    )

    assert result["status"] in {"queued", "running"}

    status = result
    for _ in range(30):
        status = get_task_status(result["job_id"], artifacts_dir=str(artifacts_dir))
        if status["status"] == "completed":
            break
        time.sleep(0.1)

    assert status["status"] == "completed"


def test_run_task_defaults_to_real_run_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifacts_dir = tmp_path / ".omniarc"

    monkeypatch.setattr(
        "omniarc.integrations.mcp.server.spawn_job",
        lambda command, *, workdir: 4242,
    )

    result = run_task(
        task="Open Finder",
        max_steps=3,
        artifacts_dir=str(artifacts_dir),
    )

    runtime_config = json.loads(
        (artifacts_dir / "runs" / result["job_id"] / "runtime_config.json").read_text(
            encoding="utf-8"
        )
    )
    assert runtime_config["runtime"]["dry_run"] is False


def test_run_task_rejects_unsupported_phrase_before_queueing(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / ".omniarc"

    result = run_task(
        task="Open Safari and go to YouTube and search for asmr",
        artifacts_dir=str(artifacts_dir),
    )

    assert result == {
        "status": "error",
        "error": "task is not supported by the current planner",
    }


def test_run_task_writes_llm_metadata_into_runtime_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifacts_dir = tmp_path / ".omniarc"

    monkeypatch.setattr(
        "omniarc.integrations.mcp.server.spawn_job",
        lambda command, *, workdir: 4242,
    )
    monkeypatch.setattr(
        "omniarc.integrations.mcp.server._validate_supported_task",
        lambda task, runtime=None, llm_config_path=None, llm_profile=None: {
            "valid": True,
            "error": None,
        },
    )

    result = run_task(
        task="Open Safari, go to YouTube, and search for asmr",
        artifacts_dir=str(artifacts_dir),
        llm_config_path="/tmp/llm_endpoints.json",
        llm_profile="fast-verified",
    )

    runtime_config = json.loads(
        (artifacts_dir / "runs" / result["job_id"] / "runtime_config.json").read_text(
            encoding="utf-8"
        )
    )
    assert runtime_config["llm"] == {
        "config_path": "/tmp/llm_endpoints.json",
        "profile": "fast-verified",
    }


def test_run_task_defaults_fast_verified_profile_when_llm_config_is_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifacts_dir = tmp_path / ".omniarc"

    monkeypatch.setattr(
        "omniarc.integrations.mcp.server.spawn_job",
        lambda command, *, workdir: 4242,
    )
    monkeypatch.setattr(
        "omniarc.integrations.mcp.server._validate_supported_task",
        lambda task, runtime=None, llm_config_path=None, llm_profile=None: {
            "valid": True,
            "error": None,
        },
    )

    result = run_task(
        task="Open Safari, go to YouTube, and search for asmr",
        artifacts_dir=str(artifacts_dir),
        llm_config_path="/tmp/llm_endpoints.json",
    )

    runtime_config = json.loads(
        (artifacts_dir / "runs" / result["job_id"] / "runtime_config.json").read_text(
            encoding="utf-8"
        )
    )
    assert runtime_config["llm"] == {
        "config_path": "/tmp/llm_endpoints.json",
        "profile": "fast-verified",
    }


def test_run_task_returns_structured_error_for_bad_llm_config_path(
    tmp_path: Path,
) -> None:
    artifacts_dir = tmp_path / ".omniarc"

    result = run_task(
        task="Open Safari, go to YouTube, and search for asmr",
        artifacts_dir=str(artifacts_dir),
        llm_config_path="/definitely/missing/llm_endpoints.json",
        llm_profile="fast-verified",
    )

    assert result["status"] == "error"
    assert "could not read llm config" in result["error"]


def test_run_task_rejects_unsupported_llm_profile(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / ".omniarc"

    result = run_task(
        task="Open Finder",
        artifacts_dir=str(artifacts_dir),
        llm_profile="slow-safe",
    )

    assert result == {"status": "error", "error": "unsupported llm profile: slow-safe"}
