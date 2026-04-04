from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from omniarc.storage.runs import ensure_run_paths


def build_runtime_config(
    *,
    base_config: dict[str, Any],
    task: str | None,
    max_steps: int | None,
    resume: bool | None,
    agent_id: str | None,
    llm_config_path: str | None = None,
    llm_profile: str | None = None,
) -> dict[str, Any]:
    config = copy.deepcopy(base_config)
    agent = config.setdefault("agent", {})
    if task is not None:
        agent["task"] = task
    if max_steps is not None:
        agent["max_steps"] = max_steps
    if resume is not None:
        agent["resume"] = bool(resume)
    if agent_id is not None:
        agent["agent_id"] = agent_id
    if llm_config_path is not None or llm_profile is not None:
        llm = config.setdefault("llm", {})
        if llm_config_path is not None:
            llm["config_path"] = llm_config_path
        if llm_profile is not None:
            llm["profile"] = llm_profile
    llm = config.get("llm")
    if isinstance(llm, dict) and llm.get("config_path") and not llm.get("profile"):
        llm["profile"] = "fast-verified"
    return config


def write_runtime_config(base_dir: Path, job_id: str, payload: dict[str, Any]) -> Path:
    run_paths = ensure_run_paths(base_dir, job_id)
    target = run_paths.root / "runtime_config.json"
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return target
