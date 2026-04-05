from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from omniarc.core.models import Action, PlanBundle, PlanStep, PreplanResult, TaskSpec
from omniarc.llm.types import LLMRequest, ProviderError


class PlannerService:
    LLM_PLANNER_SYSTEM_PROMPT = (
        'Return strict JSON with this shape: {"steps": [{"kind": <action kind>, '
        '"params": <object>}]} using only existing OmniArc action kinds.'
    )

    def __init__(self, llm_client: Any | None = None) -> None:
        self.llm_client = llm_client

    async def build(self, task: TaskSpec, preplan: PreplanResult) -> PlanBundle:
        if self.llm_client is None:
            return self._unsupported(task, preplan)
        try:
            response = await self.llm_client.complete(
                LLMRequest(
                    role="planner",
                    prompt=task.task,
                    system_prompt=self.LLM_PLANNER_SYSTEM_PROMPT,
                )
            )
        except ProviderError:
            return self._unsupported(task, preplan)
        return self._bundle_from_content(task, preplan, response.content)

    def build_sync(self, task: TaskSpec, preplan: PreplanResult) -> PlanBundle:
        if self.llm_client is None:
            return self._unsupported(task, preplan)
        try:
            response = self.llm_client.complete_sync(
                LLMRequest(
                    role="planner",
                    prompt=task.task,
                    system_prompt=self.LLM_PLANNER_SYSTEM_PROMPT,
                )
            )
        except ProviderError:
            return self._unsupported(task, preplan)
        return self._bundle_from_content(task, preplan, response.content)

    def _unsupported(self, task: TaskSpec, preplan: PreplanResult) -> PlanBundle:
        return PlanBundle(
            summary=task.task,
            status="unsupported_task",
            source="planner",
            preplan=preplan,
            steps=[],
        )

    def _bundle_from_content(
        self, task: TaskSpec, preplan: PreplanResult, content: str
    ) -> PlanBundle:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return self._unsupported(task, preplan)

        raw_steps = payload.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            return self._unsupported(task, preplan)

        steps: list[PlanStep] = []
        for raw_step in raw_steps:
            if not isinstance(raw_step, dict):
                return self._unsupported(task, preplan)
            try:
                action = Action.model_validate(raw_step)
                step = PlanStep(
                    goal=action.kind,
                    completion_hint=f"Complete action {action.kind}",
                    allowed_actions=[action.kind],
                    planned_action=action.model_dump(mode="json"),
                )
            except ValidationError:
                return self._unsupported(task, preplan)
            steps.append(step)

        return PlanBundle(
            summary=task.task,
            status="supported",
            source="planner",
            preplan=preplan,
            steps=steps,
        )
