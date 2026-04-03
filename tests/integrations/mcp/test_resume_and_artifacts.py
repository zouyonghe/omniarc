import json
import time
from pathlib import Path

from omniarc.integrations.mcp.server import (
    get_run_artifact,
    get_task_status,
    resume_task,
)
from omniarc.storage.runs import ensure_run_paths
from omniarc.storage.status import write_status


def test_get_run_artifact_lists_directories_and_binary_metadata(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    run_paths = ensure_run_paths(artifacts_dir, "job-artifacts")
    (run_paths.root / "task.json").write_text("{}\n", encoding="utf-8")
    (run_paths.observations / "latest.png").write_bytes(b"\x89PNG\r\n")

    listing = get_run_artifact("job-artifacts", "", artifacts_dir=str(artifacts_dir))
    assert "observations" in listing["entries"]

    binary = get_run_artifact(
        "job-artifacts",
        "observations/latest.png",
        artifacts_dir=str(artifacts_dir),
    )
    assert binary["kind"] == "binary"
    assert binary["size"] == 6


def test_resume_task_reuses_existing_job_checkpoint(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    run_paths = ensure_run_paths(artifacts_dir, "job-resume")
    runtime_config_path = run_paths.root / "runtime_config.json"
    runtime_config_path.write_text(
        json.dumps(
            {
                "runtime": {
                    "platform": "macos",
                    "dry_run": True,
                    "artifacts_dir": str(artifacts_dir),
                },
                "agent": {
                    "job_id": "job-resume",
                    "task": "Resume this task",
                    "max_steps": 1,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_paths.root / "task.json").write_text(
        json.dumps({"task": "Resume this task"}) + "\n",
        encoding="utf-8",
    )
    (run_paths.root / "checkpoint.json").write_text(
        json.dumps(
            {
                "status": "paused",
                "current_step": 3,
                "memory": [
                    {"kind": "summary", "content": "old", "step": 3, "metadata": {}}
                ],
                "last_actions": [],
                "last_results": [],
                "is_done": False,
                "consecutive_failures": 0,
                "last_observation": None,
                "last_decision": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    write_status(
        run_paths.root / "status.json",
        {
            "job_id": "job-resume",
            "status": "paused",
            "current_step": 3,
            "runtime_config_path": str(runtime_config_path),
        },
    )

    result = resume_task("job-resume", artifacts_dir=str(artifacts_dir), dry_run=True)
    assert result["job_id"] == "job-resume"

    status = result
    for _ in range(30):
        status = get_task_status("job-resume", artifacts_dir=str(artifacts_dir))
        if status["status"] == "completed":
            break
        time.sleep(0.1)

    assert status["status"] == "completed"
    assert status["resumed_from_step"] == 3
    assert status["current_step"] == 4


def test_resume_task_defaults_to_real_run_config(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    run_paths = ensure_run_paths(artifacts_dir, "job-resume-default")
    runtime_config_path = run_paths.root / "runtime_config.json"
    runtime_config_path.write_text(
        json.dumps(
            {
                "runtime": {
                    "platform": "macos",
                    "dry_run": True,
                    "artifacts_dir": str(artifacts_dir),
                },
                "agent": {
                    "job_id": "job-resume-default",
                    "task": "Resume this task",
                    "max_steps": 1,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_paths.root / "checkpoint.json").write_text(
        json.dumps(
            {
                "status": "paused",
                "current_step": 0,
                "memory": [],
                "last_actions": [],
                "last_results": [],
                "is_done": False,
                "consecutive_failures": 0,
                "last_observation": None,
                "last_decision": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    write_status(
        run_paths.root / "status.json",
        {
            "job_id": "job-resume-default",
            "status": "paused",
            "current_step": 0,
            "runtime_config_path": str(runtime_config_path),
        },
    )

    original_runtime_config = json.loads(
        runtime_config_path.read_text(encoding="utf-8")
    )
    assert original_runtime_config["runtime"]["dry_run"] is True

    result = resume_task("job-resume-default", artifacts_dir=str(artifacts_dir))

    resumed_runtime_config = json.loads(
        (artifacts_dir / "runs" / result["job_id"] / "runtime_config.json").read_text(
            encoding="utf-8"
        )
    )
    assert resumed_runtime_config["runtime"]["dry_run"] is False
