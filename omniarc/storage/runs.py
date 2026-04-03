from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class RunPaths:
    root: Path
    observations: Path
    records: Path
    logs: Path


def ensure_run_paths(base_dir: Path, job_id: str) -> RunPaths:
    root = base_dir / "runs" / job_id
    observations = root / "observations"
    records = root / "records"
    logs = root / "logs"
    for path in (root, observations, records, logs):
        path.mkdir(parents=True, exist_ok=True)
    return RunPaths(root=root, observations=observations, records=records, logs=logs)
