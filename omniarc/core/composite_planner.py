from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from omniarc.core.models import Action
from omniarc.core.models import TaskSpec
from omniarc.core.planner import Planner
from omniarc.llm.client import LLMClient
from omniarc.llm.types import LLMRequest, ProviderError


class CompositePlanner:
    LLM_PLANNER_SYSTEM_PROMPT = (
        'Return strict JSON with this shape: {"steps": [{"kind": <action kind>, '
        '"params": <object>}]} using only existing OmniArc action kinds.'
    )

    def __init__(
        self,
        *,
        rule_planner: Planner | None = None,
        llm_client: LLMClient | Any | None = None,
    ) -> None:
        self.rule_planner = rule_planner or Planner()
        self.llm_client = llm_client

    def _unsupported(self, task: TaskSpec, source: str) -> dict[str, Any]:
        return {
            "summary": task.task,
            "status": "unsupported_task",
            "source": source,
            "steps": [],
        }

    def _supported(
        self, task: TaskSpec, source: str, steps: list[dict[str, Any]]
    ) -> dict[str, Any]:
        return {
            "summary": task.task,
            "status": "supported",
            "source": source,
            "steps": steps,
        }

    def _llm_plan_from_content(self, task: TaskSpec, content: str) -> dict[str, Any]:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            return self._unsupported(task, "llm")

        steps = payload.get("steps")
        if not isinstance(steps, list) or not steps:
            return self._unsupported(task, "llm")

        normalized_steps: list[dict[str, Any]] = []
        for step in steps:
            try:
                normalized_steps.append(
                    Action.model_validate(step).model_dump(mode="json")
                )
            except ValidationError:
                return self._unsupported(task, "llm")

        return self._supported(task, "llm", normalized_steps)

    def plan_sync(self, task: TaskSpec) -> dict[str, Any]:
        rule_plan = self.rule_planner.plan_sync(task)
        if rule_plan.get("status") != "unsupported_task":
            return {**rule_plan, "source": "rule"}
        if self.llm_client is None:
            return {**rule_plan, "source": "rule"}

        try:
            response = self.llm_client.complete_sync(
                LLMRequest(
                    role="planner",
                    prompt=task.task,
                    system_prompt=self.LLM_PLANNER_SYSTEM_PROMPT,
                )
            )
        except ProviderError:
            return self._unsupported(task, "llm")
        return self._llm_plan_from_content(task, response.content)

    async def plan(self, task: TaskSpec) -> dict[str, Any]:
        rule_plan = await self.rule_planner.plan(task)
        if rule_plan.get("status") != "unsupported_task":
            return {**rule_plan, "source": "rule"}
        if self.llm_client is None:
            return {**rule_plan, "source": "rule"}

        try:
            response = await self.llm_client.complete(
                LLMRequest(
                    role="planner",
                    prompt=task.task,
                    system_prompt=self.LLM_PLANNER_SYSTEM_PROMPT,
                )
            )
        except ProviderError:
            return self._unsupported(task, "llm")
        return self._llm_plan_from_content(task, response.content)
