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


PlanningMode = Literal["direct", "search"]


class PreplanResult(OmniArcModel):
    planning_mode: PlanningMode = "direct"
    search_queries: list[str] = Field(default_factory=list)
    selected_skills: list[str] = Field(default_factory=list)
    success_signals: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class SearchArtifact(OmniArcModel):
    query: str
    summary: str
    source: str


class PlanStep(OmniArcModel):
    goal: str = Field(min_length=1)
    completion_hint: str
    allowed_actions: list[str] = Field(default_factory=list)
    fallback_hint: str | None = None
    planned_action: dict[str, Any] = Field(default_factory=dict)


PlanStatus = Literal["supported", "unsupported_task"]
PlanSource = Literal["rule", "llm", "preplan", "planner"]


class PlanBundle(OmniArcModel):
    summary: str
    status: PlanStatus
    source: PlanSource
    preplan: PreplanResult = Field(default_factory=PreplanResult)
    steps: list[PlanStep] = Field(default_factory=list)
    completion_criteria: list[str] = Field(default_factory=list)
    replan_triggers: list[str] = Field(default_factory=list)


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

FailureCategory = Literal[
    "wrong_app",
    "no_visible_change",
    "page_not_loaded",
    "element_not_found",
    "unsupported_task",
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


VerificationStatus = Literal[
    "progress",
    "step_complete",
    "complete",
    "wrong_app",
    "no_visible_change",
]


class VerificationResult(OmniArcModel):
    status: VerificationStatus
    failure_category: FailureCategory | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


RecoveryAction = Literal["action_retry", "strategy_retry", "replan", "fail"]


class RecoveryDecision(OmniArcModel):
    action: RecoveryAction
    failure_category: (
        FailureCategory
        | Literal["retry_budget_exhausted", "replan_budget_exhausted"]
        | None
    ) = None
    reason: str = ""


class MemoryEntry(OmniArcModel):
    kind: str = "summary"
    content: str
    step: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
