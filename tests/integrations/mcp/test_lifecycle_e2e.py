import time
from pathlib import Path

from omniarc.integrations.mcp.server import (
    get_run_artifact,
    get_task_status,
    inspect_run,
    pause_task,
    replay_run,
    resume_task,
    run_task,
)


def wait_for_status(
    job_id: str, artifacts_dir: Path, target: str, timeout: float = 5.0
) -> dict:
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        last = get_task_status(job_id, artifacts_dir=str(artifacts_dir))
        if last.get("status") == target:
            return last
        time.sleep(0.1)
    raise AssertionError(f"status did not reach {target}: {last}")


def snapshot_debug_context(job_id: str, artifacts_dir: Path) -> dict:
    return {
        "status": get_task_status(job_id, artifacts_dir=str(artifacts_dir)),
        "inspect": inspect_run(job_id, artifacts_dir=str(artifacts_dir)),
        "replay": replay_run(
            job_id, artifacts_dir=str(artifacts_dir), start=0, limit=5
        ),
        "artifacts": get_run_artifact(job_id, "", artifacts_dir=str(artifacts_dir)),
    }


def test_debug_snapshot_helper_includes_artifact_listing(tmp_path: Path) -> None:
    snapshot = snapshot_debug_context("job-1", tmp_path)
    assert "artifacts" in snapshot


def test_mcp_lifecycle_e2e(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / ".omniarc"

    started = run_task(
        task="Open Safari and search for OmniArc MCP",
        max_steps=7,
        dry_run=True,
        artifacts_dir=str(artifacts_dir),
    )

    job_id = started["job_id"]
    assert started["status"] in {"queued", "running"}, started

    paused = pause_task(job_id, artifacts_dir=str(artifacts_dir))
    assert paused["status"] == "paused", paused

    resumed = resume_task(job_id, artifacts_dir=str(artifacts_dir), dry_run=True)
    assert resumed["job_id"] == job_id, resumed

    completed = wait_for_status(job_id, artifacts_dir, "completed")
    debug = snapshot_debug_context(job_id, artifacts_dir)
    inspect_payload = inspect_run(job_id, artifacts_dir=str(artifacts_dir))
    replay_payload = replay_run(
        job_id, artifacts_dir=str(artifacts_dir), start=0, limit=10
    )
    root_listing = get_run_artifact(job_id, "", artifacts_dir=str(artifacts_dir))
    status_file = get_run_artifact(
        job_id, "status.json", artifacts_dir=str(artifacts_dir)
    )

    assert completed["status"] == "completed", debug
    assert inspect_payload["status"]["job_id"] == job_id, debug
    assert (
        inspect_payload["task"]["task"] == "Open Safari and search for OmniArc MCP"
    ), debug
    assert inspect_payload["checkpoint"] is not None, debug
    assert inspect_payload["planning"]["preplan_result"]["planning_mode"] == "direct", (
        debug
    )
    assert (
        inspect_payload["planning"]["plan_bundle"]["steps"][0]["goal"] == "open_app"
    ), debug
    assert completed["last_actions"], debug
    if "resumed_from_step" in completed:
        assert completed["resumed_from_step"] >= 0, debug
    assert any(action["kind"] == "open_app" for action in replay_payload["actions"]), (
        debug
    )
    assert replay_payload["actions"][-1]["kind"] == "done", debug
    assert replay_payload["actions"], debug
    assert replay_payload["memory"], debug
    assert replay_payload["planning"]["replan_count"] == 0, debug
    assert "observations" in root_listing["entries"], debug
    assert status_file["kind"] == "text", debug
