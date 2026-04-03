from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from omniarc.core.skills.loader import load_skills
from omniarc.integrations.mcp.bridge import build_runtime_config, write_runtime_config
from omniarc.integrations.mcp.jobs import (
    build_runner_command,
    cancel_job,
    generate_job_id,
    pause_job,
    spawn_job,
)
from omniarc.storage.runs import ensure_run_paths
from omniarc.storage.status import read_jsonl, read_status, write_status

TOOL_NAMES = [
    "health_check",
    "get_runtime_info",
    "list_skills",
    "validate_task",
    "run_task",
    "resume_task",
    "get_task_status",
    "pause_task",
    "inspect_run",
    "replay_run",
    "cancel_task",
    "get_run_artifact",
]

DEFAULT_ARTIFACTS_DIR = Path(".omniarc")
DEFAULT_SKILLS_DIR = Path("skills")

mcp = FastMCP("omniarc")


def list_tool_names() -> list[str]:
    return TOOL_NAMES[:]


def _status_path(
    job_id: str, artifacts_dir: str | Path = DEFAULT_ARTIFACTS_DIR
) -> Path:
    return Path(artifacts_dir) / "runs" / job_id / "status.json"


def _runtime_config_path(job_id: str, artifacts_dir: str | Path) -> Path:
    return Path(artifacts_dir) / "runs" / job_id / "runtime_config.json"


def _load_json(path: Path) -> dict[str, Any]:
    return read_status(path)


def _launch_job(
    *,
    job_id: str,
    runtime_config: dict[str, Any],
    artifacts_root: Path,
    resumed_from_step: int | None = None,
) -> dict[str, Any]:
    run_paths = ensure_run_paths(artifacts_root, job_id)
    runtime_config_path = write_runtime_config(artifacts_root, job_id, runtime_config)
    pid = spawn_job(build_runner_command(runtime_config_path), workdir=Path.cwd())
    status_payload = {
        "job_id": job_id,
        "status": "queued",
        "status_path": str(run_paths.root / "status.json"),
        "runtime_config_path": str(runtime_config_path),
        "current_step": resumed_from_step or 0,
        "pid": pid,
        **(
            {"resumed_from_step": resumed_from_step}
            if resumed_from_step is not None
            else {}
        ),
    }
    write_status(run_paths.root / "status.json", status_payload)
    return status_payload


@mcp.tool()
def health_check() -> dict[str, Any]:
    return {
        "status": "ok",
        "python": sys.executable,
        "artifacts_dir": str(DEFAULT_ARTIFACTS_DIR),
    }


@mcp.tool()
def get_runtime_info() -> dict[str, Any]:
    return {
        "name": "omniarc",
        "version": "0.1.0",
        "python": sys.version.split()[0],
        "transport": "stdio",
    }


@mcp.tool()
def list_skills(skills_dir: str = "skills") -> list[dict[str, Any]]:
    path = Path(skills_dir)
    if not path.exists():
        return []
    return [skill.model_dump() for skill in load_skills(path)]


@mcp.tool()
def validate_task(task: str) -> dict[str, Any]:
    cleaned = task.strip()
    return {
        "valid": bool(cleaned),
        "error": None if cleaned else "task must not be empty",
    }


@mcp.tool()
def run_task(
    task: str,
    max_steps: int | None = None,
    dry_run: bool = False,
    artifacts_dir: str = ".omniarc",
) -> dict[str, Any]:
    cleaned = task.strip()
    if not cleaned:
        return {"status": "error", "error": "task must not be empty"}

    job_id = generate_job_id()
    artifacts_root = Path(artifacts_dir)
    runtime_config = build_runtime_config(
        base_config={
            "runtime": {
                "platform": "macos",
                "dry_run": dry_run,
                "artifacts_dir": str(artifacts_root),
            },
            "agent": {"job_id": job_id},
        },
        task=cleaned,
        max_steps=max_steps,
        resume=False,
        agent_id=None,
    )
    return _launch_job(
        job_id=job_id, runtime_config=runtime_config, artifacts_root=artifacts_root
    )


@mcp.tool()
def resume_task(
    agent_id: str,
    task: str | None = None,
    max_steps: int | None = None,
    dry_run: bool = False,
    artifacts_dir: str = ".omniarc",
) -> dict[str, Any]:
    cleaned_agent_id = agent_id.strip()
    if not cleaned_agent_id:
        return {"status": "error", "error": "agent_id must not be empty"}
    artifacts_root = Path(artifacts_dir)
    runtime_config_path = _runtime_config_path(cleaned_agent_id, artifacts_root)
    if not runtime_config_path.exists():
        return {
            "status": "error",
            "error": f"runtime config not found for {cleaned_agent_id}",
        }

    existing_config = _load_json(runtime_config_path)
    checkpoint_path = artifacts_root / "runs" / cleaned_agent_id / "checkpoint.json"
    resumed_from_step = None
    if checkpoint_path.exists():
        checkpoint = _load_json(checkpoint_path)
        resumed_from_step = int(checkpoint.get("current_step", 0))

    runtime_config = build_runtime_config(
        base_config=existing_config,
        task=task
        or existing_config.get("agent", {}).get("task", f"resume:{cleaned_agent_id}"),
        max_steps=max_steps,
        resume=True,
        agent_id=cleaned_agent_id,
    )
    runtime_config.setdefault("runtime", {})["dry_run"] = dry_run
    runtime_config.setdefault("runtime", {})["artifacts_dir"] = str(artifacts_root)
    runtime_config.setdefault("agent", {})["job_id"] = cleaned_agent_id
    return _launch_job(
        job_id=cleaned_agent_id,
        runtime_config=runtime_config,
        artifacts_root=artifacts_root,
        resumed_from_step=resumed_from_step,
    )


@mcp.tool()
def get_task_status(job_id: str, artifacts_dir: str = ".omniarc") -> dict[str, Any]:
    path = _status_path(job_id, artifacts_dir)
    if not path.exists():
        return {"status": "missing", "job_id": job_id, "path": str(path)}
    return read_status(path)


@mcp.tool()
def pause_task(job_id: str, artifacts_dir: str = ".omniarc") -> dict[str, Any]:
    status = get_task_status(job_id, artifacts_dir=artifacts_dir)
    pid = status.get("pid")
    if isinstance(pid, int):
        pause_job(pid)
    status["status"] = "paused"
    status["pause_requested"] = True
    write_status(_status_path(job_id, artifacts_dir), status)
    return status


@mcp.tool()
def inspect_run(job_id: str, artifacts_dir: str = ".omniarc") -> dict[str, Any]:
    base = Path(artifacts_dir) / "runs" / job_id
    if not base.exists():
        return {"status": "missing", "job_id": job_id, "path": str(base)}

    task_path = base / "task.json"
    checkpoint_path = base / "checkpoint.json"
    status_path = base / "status.json"
    task = _load_json(task_path) if task_path.exists() else None
    checkpoint = _load_json(checkpoint_path) if checkpoint_path.exists() else None
    status = _load_json(status_path) if status_path.exists() else None
    artifacts = get_run_artifact(job_id, artifacts_dir=artifacts_dir)
    return {
        "job_id": job_id,
        "status": status,
        "task": task,
        "checkpoint": checkpoint,
        "artifacts": artifacts,
    }


@mcp.tool()
def replay_run(
    job_id: str,
    artifacts_dir: str = ".omniarc",
    start: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    base = Path(artifacts_dir) / "runs" / job_id
    actions = read_jsonl(base / "actions.jsonl")
    memory = read_jsonl(base / "memory.jsonl")
    end = start + limit
    return {
        "job_id": job_id,
        "start": start,
        "limit": limit,
        "actions": actions[start:end],
        "memory": memory[start:end],
    }


@mcp.tool()
def cancel_task(job_id: str, artifacts_dir: str = ".omniarc") -> dict[str, Any]:
    status = get_task_status(job_id, artifacts_dir=artifacts_dir)
    pid = status.get("pid")
    if isinstance(pid, int):
        cancel_job(pid)
    status["status"] = "cancelled"
    write_status(_status_path(job_id, artifacts_dir), status)
    return status


@mcp.tool()
def get_run_artifact(
    job_id: str,
    relative_path: str = "",
    artifacts_dir: str = ".omniarc",
) -> dict[str, Any]:
    base = Path(artifacts_dir) / "runs" / job_id
    target = base / relative_path if relative_path else base
    if not target.exists():
        return {"status": "missing", "path": str(target)}
    if target.is_dir():
        return {
            "status": "ok",
            "kind": "directory",
            "path": str(target),
            "entries": sorted(p.name for p in target.iterdir()),
        }
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {
            "status": "ok",
            "kind": "binary",
            "path": str(target),
            "size": target.stat().st_size,
        }
    return {
        "status": "ok",
        "kind": "text",
        "path": str(target),
        "content": content,
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
