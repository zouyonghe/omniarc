from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

PLANNING_KEYS = (
    "plan_step_index",
    "replan_count",
    "preplan_result",
    "plan_bundle",
    "search_artifacts",
)


def write_status(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        prefix=f"{path.stem}.",
        suffix=path.suffix or ".json",
    ) as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
        temp_path = handle.name
    os.replace(temp_path, path)
    return path


def read_status(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def append_jsonl(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False))
        handle.write("\n")
    return path


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            rows.append(json.loads(stripped))
    return rows


def extract_planning_payload(
    payload: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if payload is None:
        return None
    planning: dict[str, Any] = {}
    nested = payload.get("planning")
    if isinstance(nested, Mapping):
        planning.update(dict(nested))
    for key in PLANNING_KEYS:
        if key in payload and payload[key] is not None:
            planning[key] = payload[key]
    return planning or None


def merge_planning_payloads(
    *payloads: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    merged: dict[str, Any] = {}
    for payload in payloads:
        extracted = extract_planning_payload(payload)
        if extracted:
            merged.update(extracted)
    return merged or None
