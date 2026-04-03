from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OmniArcModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskSpec(OmniArcModel):
    task: str
    host: str | None = None
    runtime: str | None = None
    allow_search: bool = False
    available_skills: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)


class RunConfig(OmniArcModel):
    max_steps: int = 100
    max_retries: int = 2
    runtime: str | None = None
    artifacts_dir: str = ".omniarc"
    resume: bool = False


class Observation(OmniArcModel):
    screenshot_path: str
    active_app: str
    window_title: str | None = None
    ui_tree: dict[str, Any] | None = None
    ocr_blocks: list[dict[str, Any]] = Field(default_factory=list)
    platform_metadata: dict[str, Any] = Field(default_factory=dict)


class Decision(OmniArcModel):
    step_evaluation: str = "unknown"
    reasoning: str = ""
    next_goal: str = ""
    ask_human: str = "No"
    selected_skills: list[str] = Field(default_factory=list)
    planned_action: dict[str, Any] = Field(default_factory=dict)


ActionKind = Literal[
    "click",
    "double_click",
    "type_text",
    "press_key",
    "hotkey",
    "scroll",
    "drag",
    "wait",
    "done",
    "open_app",
    "run_command",
    "run_script",
    "record_info",
    "run_applescript",
    "run_powershell",
]


class Action(OmniArcModel):
    kind: ActionKind
    params: dict[str, Any] = Field(default_factory=dict)


class ActionResult(OmniArcModel):
    success: bool = True
    error_type: str | None = None
    error_message: str | None = None
    extracted_content: str | None = None
    is_done: bool = False


class MemoryEntry(OmniArcModel):
    kind: str = "summary"
    content: str
    step: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
