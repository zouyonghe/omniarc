from __future__ import annotations

import os
import signal
import subprocess
import sys
import uuid
from pathlib import Path


def generate_job_id() -> str:
    return str(uuid.uuid4())


def spawn_job(command: list[str], *, workdir: Path) -> int:
    process = subprocess.Popen(
        command,
        cwd=str(workdir),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return process.pid


def cancel_job(pid: int) -> None:
    os.kill(pid, signal.SIGTERM)


def pause_job(pid: int) -> None:
    os.kill(pid, signal.SIGUSR1)


def build_runner_command(config_path: Path) -> list[str]:
    return [sys.executable, "-m", "omniarc", "--config", str(config_path)]
