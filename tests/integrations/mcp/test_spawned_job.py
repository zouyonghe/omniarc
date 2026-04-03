import time
import json
from pathlib import Path

from omniarc.integrations.mcp.server import get_task_status, run_task


def test_run_task_spawns_background_dry_run(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / ".omniarc"
    result = run_task(
        task="Do one thing",
        max_steps=1,
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


def test_run_task_defaults_to_real_run_config(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / ".omniarc"

    result = run_task(
        task="Do one thing",
        max_steps=1,
        artifacts_dir=str(artifacts_dir),
    )

    runtime_config = json.loads(
        (artifacts_dir / "runs" / result["job_id"] / "runtime_config.json").read_text(
            encoding="utf-8"
        )
    )
    assert runtime_config["runtime"]["dry_run"] is False
