from __future__ import annotations

import asyncio
import json
import signal
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from omniarc.core.agent import OmniArcAgent
from omniarc.core.models import TaskSpec
from omniarc.core.state import RunState
from omniarc.runtimes.macos.executor import MacOSExecutor
from omniarc.runtimes.macos.observer import MacOSObserver
from omniarc.runtimes.windows.executor import WindowsExecutor
from omniarc.runtimes.windows.observer import WindowsObserver
from omniarc.storage.runs import ensure_run_paths
from omniarc.storage.status import append_jsonl, read_status, write_status


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def run_from_config(path: Path):
    config = load_config(path)
    runtime_config = config.get("runtime", {})
    agent_config = config.get("agent", {})

    platform = runtime_config.get("platform", "macos")
    if platform not in {"macos", "windows"}:
        raise ValueError(f"Unsupported runtime platform: {platform}")

    artifacts_dir = Path(runtime_config.get("artifacts_dir", ".omniarc"))
    job_id = str(agent_config.get("job_id", "default-job"))
    run_paths = ensure_run_paths(artifacts_dir, job_id)
    status_path = run_paths.root / "status.json"
    task_path = run_paths.root / "task.json"
    checkpoint_path = run_paths.root / "checkpoint.json"
    actions_path = run_paths.root / "actions.jsonl"
    memory_path = run_paths.root / "memory.jsonl"
    resumed_from_step: int | None = None

    _write_json(
        task_path,
        {
            "task": str(agent_config.get("task", "")),
            "job_id": job_id,
            "runtime": platform,
        },
    )

    state: RunState | None = None
    if agent_config.get("resume") and checkpoint_path.exists():
        state = RunState.model_validate(
            json.loads(checkpoint_path.read_text(encoding="utf-8"))
        )
        resumed_from_step = state.current_step

    pause_requested = False

    def _handle_pause_signal(
        signum, frame
    ) -> None:  # pragma: no cover - signal delivery is nondeterministic in unit tests
        nonlocal pause_requested
        pause_requested = True

    previous_usr1 = signal.signal(signal.SIGUSR1, _handle_pause_signal)

    write_status(
        status_path,
        {
            "job_id": job_id,
            "status": "running",
            "current_step": state.current_step if state else 0,
            "runtime_config_path": str(path),
            "task_path": str(task_path),
            "checkpoint_path": str(checkpoint_path),
            "actions_path": str(actions_path),
            "memory_path": str(memory_path),
            "updated_at": _now_iso(),
            **(
                {"resumed_from_step": resumed_from_step}
                if resumed_from_step is not None
                else {}
            ),
        },
    )

    if platform == "macos":
        observer = MacOSObserver(
            artifacts_dir=run_paths.observations,
            dry_run=bool(runtime_config.get("dry_run", False)),
        )
        executor = MacOSExecutor(dry_run=bool(runtime_config.get("dry_run", False)))
    else:
        observer = WindowsObserver(
            artifacts_dir=run_paths.observations,
            dry_run=bool(runtime_config.get("dry_run", False)),
        )
        executor = WindowsExecutor(dry_run=bool(runtime_config.get("dry_run", False)))
    starting_memory_count = len(state.memory) if state else 0
    starting_action_count = len(state.action_history) if state else 0
    agent = OmniArcAgent.build_for_test(
        observer=observer,
        executor=executor,
        task=TaskSpec(task=str(agent_config.get("task", ""))),
        state=state,
        should_pause=lambda: pause_requested,
    )

    try:
        state = asyncio.run(
            agent.run(max_steps=int(agent_config.get("max_steps", 100)))
        )
    finally:
        signal.signal(signal.SIGUSR1, previous_usr1)
    for action in state.action_history[starting_action_count:]:
        append_jsonl(actions_path, action.model_dump(mode="json"))
    for entry in state.memory[starting_memory_count:]:
        append_jsonl(memory_path, entry.model_dump(mode="json"))
    _write_json(checkpoint_path, state.model_dump(mode="json"))
    existing_status = read_status(status_path)
    write_status(
        status_path,
        {
            "job_id": job_id,
            "status": state.status,
            "current_step": state.current_step,
            "history_length": len(state.memory),
            "runtime_config_path": str(path),
            "task_path": str(task_path),
            "checkpoint_path": str(checkpoint_path),
            "actions_path": str(actions_path),
            "memory_path": str(memory_path),
            "last_actions": [
                action.model_dump(mode="json") for action in state.last_actions
            ],
            "last_step_evaluation": (
                state.last_decision.step_evaluation if state.last_decision else None
            ),
            "next_goal": state.last_decision.next_goal if state.last_decision else "",
            "last_observation_path": (
                state.last_observation.screenshot_path
                if state.last_observation
                else None
            ),
            "updated_at": _now_iso(),
            **({"pid": existing_status["pid"]} if "pid" in existing_status else {}),
            **(
                {"resumed_from_step": resumed_from_step}
                if resumed_from_step is not None
                else {}
            ),
        },
    )
    return state
