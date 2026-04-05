import json
from pathlib import Path

import pytest

from omniarc.core.models import Action, VerificationResult
from omniarc.core.state import RunState
from omniarc.llm.types import LLMResponse
from omniarc.runtime_runner import run_from_config


def test_run_from_config_completes_dry_run_job(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "runtime": {
                    "platform": "macos",
                    "dry_run": True,
                    "artifacts_dir": str(artifacts_dir),
                },
                "agent": {
                    "job_id": "job-123",
                    "task": "Open Finder",
                    "max_steps": 3,
                },
            }
        ),
        encoding="utf-8",
    )

    state = run_from_config(config_path)

    assert state.status == "completed"
    status_path = artifacts_dir / "runs" / "job-123" / "status.json"
    assert status_path.exists()


def test_run_from_config_writes_richer_status_and_artifacts(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "runtime": {
                    "platform": "macos",
                    "dry_run": True,
                    "artifacts_dir": str(artifacts_dir),
                },
                "agent": {
                    "job_id": "job-456",
                    "task": "Open Finder",
                    "max_steps": 3,
                },
            }
        ),
        encoding="utf-8",
    )

    run_from_config(config_path)

    run_root = artifacts_dir / "runs" / "job-456"
    status = json.loads((run_root / "status.json").read_text(encoding="utf-8"))

    assert (run_root / "task.json").exists()
    assert (run_root / "checkpoint.json").exists()
    assert (run_root / "actions.jsonl").exists()
    assert (run_root / "memory.jsonl").exists()
    assert status["last_actions"][0]["kind"] == "done"
    assert status["last_step_evaluation"] == "success"
    assert status["last_observation_path"].endswith("latest.png")
    assert status["last_verification"]["status"] == "complete"
    assert status["last_recovery"] is None
    checkpoint = json.loads((run_root / "checkpoint.json").read_text(encoding="utf-8"))
    assert checkpoint["last_verification"]["status"] == "complete"
    assert checkpoint["action_retry_count"] == 0
    assert checkpoint["strategy_retry_count"] == 0
    assert checkpoint["preplan_result"]["planning_mode"] == "direct"
    assert checkpoint["plan_bundle"]["steps"][0]["goal"] == "open_app"
    assert checkpoint["search_artifacts"] == []
    assert checkpoint["replan_count"] == 0
    assert status["planning"]["preplan_result"]["planning_mode"] == "direct"
    assert status["planning"]["plan_bundle"]["steps"][0]["goal"] == "open_app"
    assert status["planning"]["replan_count"] == 0


def test_run_from_config_supports_windows_dry_run(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    config_path = tmp_path / "windows-config.json"
    config_path.write_text(
        json.dumps(
            {
                "runtime": {
                    "platform": "windows",
                    "dry_run": True,
                    "artifacts_dir": str(artifacts_dir),
                },
                "agent": {
                    "job_id": "job-win-123",
                    "task": "Open Notepad",
                    "max_steps": 3,
                },
            }
        ),
        encoding="utf-8",
    )

    state = run_from_config(config_path)

    assert state.status == "completed"
    status = json.loads(
        (artifacts_dir / "runs" / "job-win-123" / "status.json").read_text(
            encoding="utf-8"
        )
    )
    actions = (artifacts_dir / "runs" / "job-win-123" / "actions.jsonl").read_text(
        encoding="utf-8"
    )
    assert status["last_observation_path"].endswith("latest.png")
    assert '"kind": "open_app"' in actions


def test_run_from_config_does_not_launch_notepad_on_macos(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    config_path = tmp_path / "macos-notepad-config.json"
    config_path.write_text(
        json.dumps(
            {
                "runtime": {
                    "platform": "macos",
                    "dry_run": True,
                    "artifacts_dir": str(artifacts_dir),
                },
                "agent": {
                    "job_id": "job-macos-notepad",
                    "task": "Open Notepad",
                    "max_steps": 1,
                },
            }
        ),
        encoding="utf-8",
    )

    state = run_from_config(config_path)

    assert state.status == "failed"
    assert state.action_history == []
    run_root = artifacts_dir / "runs" / "job-macos-notepad"
    status = json.loads((run_root / "status.json").read_text(encoding="utf-8"))
    assert status["last_actions"] == []
    assert not (run_root / "actions.jsonl").exists()


def test_run_from_config_records_non_terminal_action_history(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    config_path = tmp_path / "multi-step-config.json"
    config_path.write_text(
        json.dumps(
            {
                "runtime": {
                    "platform": "macos",
                    "dry_run": True,
                    "artifacts_dir": str(artifacts_dir),
                },
                "agent": {
                    "job_id": "job-789",
                    "task": "Open Finder",
                    "max_steps": 3,
                },
            }
        ),
        encoding="utf-8",
    )

    run_from_config(config_path)

    actions = (artifacts_dir / "runs" / "job-789" / "actions.jsonl").read_text(
        encoding="utf-8"
    )
    assert '"kind": "open_app"' in actions


def test_run_from_config_records_scroll_history_for_map_zoom_task(
    tmp_path: Path,
) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    config_path = tmp_path / "map-zoom-config.json"
    config_path.write_text(
        json.dumps(
            {
                "runtime": {
                    "platform": "macos",
                    "dry_run": True,
                    "artifacts_dir": str(artifacts_dir),
                },
                "agent": {
                    "job_id": "job-map-zoom",
                    "task": "Open Safari and go to google.com/maps/place/Washington and zoom in",
                    "max_steps": 10,
                },
            }
        ),
        encoding="utf-8",
    )

    run_from_config(config_path)

    action_lines = (
        artifacts_dir / "runs" / "job-map-zoom" / "actions.jsonl"
    ).read_text(encoding="utf-8")
    actions = [json.loads(line) for line in action_lines.splitlines() if line.strip()]
    assert any(action["kind"] == "scroll" for action in actions)


def test_run_from_config_fails_for_unsupported_task_without_actions(
    tmp_path: Path,
) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    config_path = tmp_path / "unsupported-config.json"
    config_path.write_text(
        json.dumps(
            {
                "runtime": {
                    "platform": "macos",
                    "dry_run": True,
                    "artifacts_dir": str(artifacts_dir),
                },
                "agent": {
                    "job_id": "job-unsupported",
                    "task": "Open Safari, go to YouTube, and search for asmr",
                    "max_steps": 5,
                },
            }
        ),
        encoding="utf-8",
    )

    state = run_from_config(config_path)

    assert state.status == "failed"
    assert state.current_step == 0
    assert state.last_actions == []
    assert state.action_history == []
    assert state.last_decision is not None
    assert state.last_decision.step_evaluation == "unsupported_task"

    run_root = artifacts_dir / "runs" / "job-unsupported"
    status = json.loads((run_root / "status.json").read_text(encoding="utf-8"))
    assert status["status"] == "failed"
    assert status["history_length"] == 0
    assert status["last_actions"] == []
    assert status["last_step_evaluation"] == "unsupported_task"
    assert not (run_root / "actions.jsonl").exists()


def test_run_from_config_records_scroll_history_for_page_scroll_task(
    tmp_path: Path,
) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    config_path = tmp_path / "page-scroll-config.json"
    config_path.write_text(
        json.dumps(
            {
                "runtime": {
                    "platform": "macos",
                    "dry_run": True,
                    "artifacts_dir": str(artifacts_dir),
                },
                "agent": {
                    "job_id": "job-page-scroll",
                    "task": "Open Safari and go to en.wikipedia.org/wiki/Washington,_D.C. and scroll down",
                    "max_steps": 10,
                },
            }
        ),
        encoding="utf-8",
    )

    run_from_config(config_path)

    action_lines = (
        artifacts_dir / "runs" / "job-page-scroll" / "actions.jsonl"
    ).read_text(encoding="utf-8")
    actions = [json.loads(line) for line in action_lines.splitlines() if line.strip()]
    assert any(action["kind"] == "scroll" for action in actions)


def test_run_from_config_persists_recovery_state_for_failed_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    config_path = tmp_path / "failed-verification-config.json"
    config_path.write_text(
        json.dumps(
            {
                "runtime": {
                    "platform": "macos",
                    "dry_run": True,
                    "artifacts_dir": str(artifacts_dir),
                },
                "agent": {
                    "job_id": "job-failed-verification",
                    "task": "Open Finder",
                    "max_steps": 1,
                },
            }
        ),
        encoding="utf-8",
    )

    def fake_verify(self, *, task_text, actions, before, after):
        return VerificationResult(
            status="no_visible_change",
            failure_category="no_visible_change",
            evidence={"reason": "forced test verification failure"},
        )

    monkeypatch.setattr("omniarc.core.agent.StepVerifier.verify", fake_verify)

    state = run_from_config(config_path)

    run_root = artifacts_dir / "runs" / "job-failed-verification"
    status = json.loads((run_root / "status.json").read_text(encoding="utf-8"))
    checkpoint = json.loads((run_root / "checkpoint.json").read_text(encoding="utf-8"))
    assert state.status == "failed"
    assert status["last_verification"]["status"] == "no_visible_change"
    assert status["last_recovery"]["action"] == "action_retry"
    assert checkpoint["action_retry_count"] == 1
    assert checkpoint["strategy_retry_count"] == 0


def test_run_from_config_uses_llm_fallback_planner_when_llm_config_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    llm_config_path = tmp_path / "llm_endpoints.json"
    llm_config_path.write_text(
        json.dumps({"endpoints": [], "roles": {}}), encoding="utf-8"
    )
    config_path = tmp_path / "llm-fallback-config.json"
    config_path.write_text(
        json.dumps(
            {
                "runtime": {
                    "platform": "macos",
                    "dry_run": True,
                    "artifacts_dir": str(artifacts_dir),
                },
                "llm": {
                    "config_path": str(llm_config_path),
                    "profile": "fast-verified",
                },
                "agent": {
                    "job_id": "job-llm-fallback",
                    "task": "Open Safari, go to YouTube, and search for asmr",
                    "max_steps": 3,
                },
            }
        ),
        encoding="utf-8",
    )

    class FakePlanner:
        async def plan(self, task):
            return {
                "status": "supported",
                "source": "llm",
                "steps": [{"kind": "done", "params": {}}],
            }

    monkeypatch.setattr(
        "omniarc.runtime_runner._build_planner_from_config",
        lambda config: FakePlanner(),
    )

    state = run_from_config(config_path)

    assert state.status == "completed"


def test_run_from_config_defaults_to_fast_verified_when_llm_config_is_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    llm_config_path = tmp_path / "llm_endpoints.json"
    llm_config_path.write_text(
        json.dumps(
            {
                "endpoints": [
                    {
                        "name": "primary",
                        "provider": "openai_compatible",
                        "base_url": "https://api.openai.com/v1",
                        "api_key": "test-key",
                        "model": "gpt-4o-mini",
                        "priority": 1,
                        "enabled": True,
                        "timeout": 30,
                    }
                ],
                "roles": {},
            }
        ),
        encoding="utf-8",
    )
    config_path = tmp_path / "llm-default-profile-config.json"
    config_path.write_text(
        json.dumps(
            {
                "runtime": {
                    "platform": "macos",
                    "dry_run": True,
                    "artifacts_dir": str(artifacts_dir),
                },
                "llm": {
                    "config_path": str(llm_config_path),
                },
                "agent": {
                    "job_id": "job-llm-default-profile",
                    "task": "Open Safari, go to YouTube, and search for asmr",
                    "max_steps": 3,
                },
            }
        ),
        encoding="utf-8",
    )

    async def fake_complete(self, endpoint, request):
        return LLMResponse(
            content='{"steps":[{"kind":"done","params":{}}]}',
            provider=endpoint.provider,
            model=endpoint.model,
        )

    monkeypatch.setattr(
        "omniarc.llm.providers.openai_compatible.OpenAICompatibleProvider.complete",
        fake_complete,
    )

    state = run_from_config(config_path)

    assert state.status == "completed"


def test_run_from_config_marks_status_failed_when_llm_profile_config_is_unusable(
    tmp_path: Path,
) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    llm_config_path = tmp_path / "llm_endpoints.json"
    llm_config_path.write_text(
        json.dumps({"endpoints": [], "roles": {}}), encoding="utf-8"
    )
    config_path = tmp_path / "llm-invalid-runtime.json"
    config_path.write_text(
        json.dumps(
            {
                "runtime": {
                    "platform": "macos",
                    "dry_run": True,
                    "artifacts_dir": str(artifacts_dir),
                },
                "llm": {
                    "config_path": str(llm_config_path),
                    "profile": "fast-verified",
                },
                "agent": {
                    "job_id": "job-llm-invalid-runtime",
                    "task": "Open Safari, go to YouTube, and search for asmr",
                    "max_steps": 3,
                },
            }
        ),
        encoding="utf-8",
    )

    state = run_from_config(config_path)

    run_root = artifacts_dir / "runs" / "job-llm-invalid-runtime"
    status = json.loads((run_root / "status.json").read_text(encoding="utf-8"))
    assert state.status == "failed"
    assert status["status"] == "failed"
    assert "no enabled llm endpoints configured" in status["error"]["message"]


def test_run_from_config_persists_minimal_artifacts_on_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    config_path = tmp_path / "exception-config.json"
    config_path.write_text(
        json.dumps(
            {
                "runtime": {
                    "platform": "macos",
                    "dry_run": True,
                    "artifacts_dir": str(artifacts_dir),
                },
                "agent": {
                    "job_id": "job-exception",
                    "task": "Open Finder",
                    "max_steps": 3,
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "omniarc.runtime_runner._build_planner_from_config",
        lambda config: (_ for _ in ()).throw(RuntimeError("planner blew up")),
    )

    state = run_from_config(config_path)

    run_root = artifacts_dir / "runs" / "job-exception"
    status = json.loads((run_root / "status.json").read_text(encoding="utf-8"))
    checkpoint = json.loads((run_root / "checkpoint.json").read_text(encoding="utf-8"))
    assert state.status == "failed"
    assert status["status"] == "failed"
    assert status["error"]["message"] == "planner blew up"
    assert checkpoint["status"] == "failed"
    assert (run_root / "actions.jsonl").exists()
    assert (run_root / "memory.jsonl").exists()


def test_run_from_config_persists_partial_agent_state_on_runtime_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    config_path = tmp_path / "runtime-exception-config.json"
    config_path.write_text(
        json.dumps(
            {
                "runtime": {
                    "platform": "macos",
                    "dry_run": True,
                    "artifacts_dir": str(artifacts_dir),
                },
                "agent": {
                    "job_id": "job-runtime-exception",
                    "task": "Open Finder",
                    "max_steps": 3,
                },
            }
        ),
        encoding="utf-8",
    )

    class CrashingAgent:
        def __init__(self):
            self.state = RunState(
                status="acting",
                current_step=1,
                last_actions=[Action(kind="open_app", params={"name": "Finder"})],
                action_history=[Action(kind="open_app", params={"name": "Finder"})],
                last_verification=VerificationResult(
                    status="progress", evidence={"matched_app": "Finder"}
                ),
            )

        async def run(self, max_steps: int):
            raise RuntimeError("executor exploded")

    monkeypatch.setattr(
        "omniarc.runtime_runner.OmniArcAgent.build_for_test",
        lambda **kwargs: CrashingAgent(),
    )

    state = run_from_config(config_path)

    run_root = artifacts_dir / "runs" / "job-runtime-exception"
    status = json.loads((run_root / "status.json").read_text(encoding="utf-8"))
    checkpoint = json.loads((run_root / "checkpoint.json").read_text(encoding="utf-8"))
    actions = (run_root / "actions.jsonl").read_text(encoding="utf-8")
    assert state.status == "failed"
    assert status["status"] == "failed"
    assert status["last_verification"]["status"] == "progress"
    assert checkpoint["last_verification"]["status"] == "progress"
    assert '"kind": "open_app"' in actions


def test_run_from_config_marks_status_failed_when_runtime_init_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    config_path = tmp_path / "init-exception-config.json"
    config_path.write_text(
        json.dumps(
            {
                "runtime": {
                    "platform": "macos",
                    "dry_run": True,
                    "artifacts_dir": str(artifacts_dir),
                },
                "agent": {
                    "job_id": "job-init-exception",
                    "task": "Open Finder",
                    "max_steps": 3,
                },
            }
        ),
        encoding="utf-8",
    )

    def raise_init(*args, **kwargs):
        raise RuntimeError("observer init failed")

    monkeypatch.setattr("omniarc.runtime_runner.MacOSObserver", raise_init)

    state = run_from_config(config_path)

    run_root = artifacts_dir / "runs" / "job-init-exception"
    status = json.loads((run_root / "status.json").read_text(encoding="utf-8"))
    assert state.status == "failed"
    assert status["status"] == "failed"
    assert status["error"]["message"] == "observer init failed"


def test_run_from_config_keeps_explicit_plan_step_index_on_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    run_paths = artifacts_dir / "runs" / "job-plan-step-index"
    run_paths.mkdir(parents=True, exist_ok=True)
    config_path = tmp_path / "resume-config.json"
    config_path.write_text(
        json.dumps(
            {
                "runtime": {
                    "platform": "macos",
                    "dry_run": True,
                    "artifacts_dir": str(artifacts_dir),
                },
                "agent": {
                    "job_id": "job-plan-step-index",
                    "task": "Open Finder",
                    "max_steps": 3,
                    "resume": True,
                },
            }
        ),
        encoding="utf-8",
    )
    (run_paths / "checkpoint.json").write_text(
        json.dumps(
            {
                "status": "paused",
                "current_step": 5,
                "plan_step_index": 0,
                "memory": [],
                "last_actions": [],
                "last_results": [],
                "is_done": False,
                "consecutive_failures": 0,
                "last_observation": None,
                "last_decision": None,
                "last_verification": None,
                "last_recovery": None,
                "action_retry_count": 0,
                "strategy_retry_count": 0,
            }
        ),
        encoding="utf-8",
    )

    captured = {}

    class CapturingAgent:
        def __init__(self, *, state, **kwargs):
            captured["plan_step_index"] = state.plan_step_index
            self.state = state

        async def run(self, max_steps: int):
            self.state.status = "completed"
            return self.state

    monkeypatch.setattr(
        "omniarc.runtime_runner.OmniArcAgent.build_for_test",
        lambda **kwargs: CapturingAgent(**kwargs),
    )

    run_from_config(config_path)

    assert captured["plan_step_index"] == 0


def test_run_from_config_hydrates_missing_planner_fields_on_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    run_root = artifacts_dir / "runs" / "job-old-checkpoint"
    run_root.mkdir(parents=True, exist_ok=True)
    config_path = tmp_path / "resume-old-config.json"
    config_path.write_text(
        json.dumps(
            {
                "runtime": {
                    "platform": "macos",
                    "dry_run": True,
                    "artifacts_dir": str(artifacts_dir),
                },
                "agent": {
                    "job_id": "job-old-checkpoint",
                    "task": "Open Finder",
                    "max_steps": 1,
                    "resume": True,
                },
            }
        ),
        encoding="utf-8",
    )
    (run_root / "checkpoint.json").write_text(
        json.dumps(
            {
                "status": "paused",
                "current_step": 2,
                "plan_step_index": 0,
                "memory": [],
                "last_actions": [],
                "last_results": [],
                "is_done": False,
                "consecutive_failures": 0,
                "last_observation": None,
                "last_decision": None,
                "last_verification": None,
                "last_recovery": None,
                "action_retry_count": 0,
                "strategy_retry_count": 0,
            }
        ),
        encoding="utf-8",
    )

    captured = {}

    class CapturingAgent:
        def __init__(self, *, state, **kwargs):
            captured["preplan_result"] = state.preplan_result
            captured["plan_bundle"] = state.plan_bundle
            captured["search_artifacts"] = state.search_artifacts
            captured["replan_count"] = state.replan_count
            self.state = state

        async def run(self, max_steps: int):
            self.state.status = "completed"
            return self.state

    monkeypatch.setattr(
        "omniarc.runtime_runner.OmniArcAgent.build_for_test",
        lambda **kwargs: CapturingAgent(**kwargs),
    )

    run_from_config(config_path)

    assert captured["preplan_result"] is None
    assert captured["plan_bundle"] is None
    assert captured["search_artifacts"] == []
    assert captured["replan_count"] == 0


def test_run_from_config_completes_page_zoom_example_config(tmp_path: Path) -> None:
    config = json.loads(
        Path("examples/macos.page-zoom.json").read_text(encoding="utf-8")
    )
    config["runtime"]["artifacts_dir"] = str(tmp_path / ".omniarc")
    config_path = tmp_path / "page-zoom-example.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    state = run_from_config(config_path)

    assert state.status == "completed"


def test_run_from_config_completes_page_scroll_example_config(tmp_path: Path) -> None:
    config = json.loads(
        Path("examples/macos.page-scroll.json").read_text(encoding="utf-8")
    )
    config["runtime"]["artifacts_dir"] = str(tmp_path / ".omniarc")
    config_path = tmp_path / "page-scroll-example.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    state = run_from_config(config_path)

    assert state.status == "completed"
