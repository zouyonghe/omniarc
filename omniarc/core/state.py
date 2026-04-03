from __future__ import annotations

from pydantic import Field

from omniarc.core.models import (
    Action,
    ActionResult,
    Decision,
    MemoryEntry,
    Observation,
    OmniArcModel,
)


class RunState(OmniArcModel):
    status: str = "queued"
    current_step: int = 0
    consecutive_failures: int = 0
    last_observation: Observation | None = None
    last_decision: Decision | None = None
    last_actions: list[Action] = Field(default_factory=list)
    action_history: list[Action] = Field(default_factory=list)
    last_results: list[ActionResult] = Field(default_factory=list)
    memory: list[MemoryEntry] = Field(default_factory=list)
    is_done: bool = False


class JobStatus(OmniArcModel):
    job_id: str
    status: str = "queued"
    current_step: int = 0
    next_goal: str = ""
    history_length: int = 0
    wait_this_step: bool = False
    last_actions: list[dict] = Field(default_factory=list)
    last_step_evaluation: str | None = None
    error: dict | None = None
