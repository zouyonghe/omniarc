import json
import os
import signal
import subprocess
from pathlib import Path

from omniarc.integrations.mcp.server import inspect_run, pause_task, replay_run
from omniarc.storage.runs import ensure_run_paths
from omniarc.storage.status import append_jsonl, write_status


def test_pause_task_marks_status_paused(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    run_paths = ensure_run_paths(artifacts_dir, "job-pause")
    sleeper = subprocess.Popen(
        [
            "python3",
            "-c",
            "import signal, time; signal.signal(signal.SIGUSR1, lambda *_: None); time.sleep(5)",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    try:
        write_status(
            run_paths.root / "status.json",
            {
                "job_id": "job-pause",
                "status": "running",
                "current_step": 2,
                "pid": sleeper.pid,
            },
        )
        status = pause_task("job-pause", artifacts_dir=str(artifacts_dir))
        assert status["status"] == "paused"
        assert status["pause_requested"] is True
    finally:
        os.kill(sleeper.pid, signal.SIGTERM)
        sleeper.wait(timeout=5)


def test_inspect_run_returns_status_task_checkpoint_and_artifacts(
    tmp_path: Path,
) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    run_paths = ensure_run_paths(artifacts_dir, "job-inspect")
    (run_paths.root / "task.json").write_text(
        json.dumps({"task": "Inspect me"}) + "\n",
        encoding="utf-8",
    )
    (run_paths.root / "checkpoint.json").write_text(
        json.dumps({"current_step": 4, "status": "paused"}) + "\n",
        encoding="utf-8",
    )
    (run_paths.observations / "latest.png").write_bytes(b"\x89PNG\r\n")
    write_status(
        run_paths.root / "status.json",
        {"job_id": "job-inspect", "status": "paused", "current_step": 4},
    )

    result = inspect_run("job-inspect", artifacts_dir=str(artifacts_dir))

    assert result["status"]["status"] == "paused"
    assert result["task"]["task"] == "Inspect me"
    assert result["checkpoint"]["current_step"] == 4
    assert "observations" in result["artifacts"]["entries"]


def test_replay_run_reads_actions_and_memory_timeline(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    run_paths = ensure_run_paths(artifacts_dir, "job-replay")
    append_jsonl(
        run_paths.root / "actions.jsonl", {"kind": "click", "params": {"x": 1, "y": 2}}
    )
    append_jsonl(run_paths.root / "actions.jsonl", {"kind": "done", "params": {}})
    append_jsonl(
        run_paths.root / "memory.jsonl",
        {"kind": "summary", "content": "step one", "step": 1, "metadata": {}},
    )

    result = replay_run(
        "job-replay", artifacts_dir=str(artifacts_dir), start=0, limit=10
    )

    assert result["actions"][0]["kind"] == "click"
    assert result["actions"][1]["kind"] == "done"
    assert result["memory"][0]["content"] == "step one"
