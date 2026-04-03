from pathlib import Path

from omniarc.storage.runs import ensure_run_paths
from omniarc.storage.status import write_status


def test_ensure_run_paths_creates_expected_layout(tmp_path: Path) -> None:
    paths = ensure_run_paths(tmp_path, "job-123")
    assert paths.root.name == "job-123"
    assert paths.observations.exists()
    assert paths.logs.exists()


def test_write_status_overwrites_atomically(tmp_path: Path) -> None:
    target = tmp_path / "status.json"
    write_status(target, {"status": "queued"})
    assert target.read_text(encoding="utf-8").strip().startswith("{")
