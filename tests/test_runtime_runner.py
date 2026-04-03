import json
from pathlib import Path

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
                    "task": "Do one thing",
                    "max_steps": 1,
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
                    "task": "Do one thing",
                    "max_steps": 1,
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

    assert state.status == "completed"
    actions = (
        artifacts_dir / "runs" / "job-macos-notepad" / "actions.jsonl"
    ).read_text(encoding="utf-8")
    assert '"kind": "open_app"' not in actions


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
