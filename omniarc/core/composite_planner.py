from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from omniarc.core.models import PlanBundle, PlanStep, PreplanResult, TaskSpec
from omniarc.core.planner import Planner
from omniarc.core.planner_service import PlannerService
from omniarc.core.preplan_service import PreplanService


class CompositePlanner:
    def __init__(
        self,
        *,
        rule_planner: Planner | None = None,
        preplan_service: PreplanService | Any | None = None,
        planner_service: PlannerService | Any | None = None,
        llm_client: Any | None = None,
    ) -> None:
        self.rule_planner = rule_planner or Planner()
        self.preplan_service = preplan_service or PreplanService()
        self.planner_service = planner_service or PlannerService(llm_client=llm_client)
        self.llm_client = llm_client

    def _unsupported(
        self, task: TaskSpec, source: str, preplan: PreplanResult | None = None
    ) -> PlanBundle:
        return PlanBundle(
            summary=task.task,
            status="unsupported_task",
            source=source,
            preplan=preplan or PreplanResult(),
            steps=[],
        )

    def _normalize_rule_plan(self, task: TaskSpec, plan: dict[str, Any]) -> PlanBundle:
        status = plan.get("status", "unsupported_task")
        if status == "unsupported_task":
            return self._unsupported(task, "rule")

        steps = [
            PlanStep(
                goal=str(step["kind"]),
                completion_hint=f"Complete action {step['kind']}",
                allowed_actions=[str(step["kind"])],
                planned_action=dict(step),
            )
            for step in plan.get("steps", [])
        ]
        return PlanBundle(
            summary=str(plan.get("summary", task.task)),
            status="supported",
            source="rule",
            steps=steps,
        )

    def _normalize_planner_output(self, task: TaskSpec, payload: Any) -> PlanBundle:
        try:
            plan = (
                payload
                if isinstance(payload, PlanBundle)
                else PlanBundle.model_validate(payload)
            )
        except ValidationError:
            return self._unsupported(task, "planner")

        if plan.status == "unsupported_task":
            return self._unsupported(task, plan.source, plan.preplan)
        return plan

    async def plan(self, task: TaskSpec) -> PlanBundle:
        rule_plan = self._normalize_rule_plan(task, await self.rule_planner.plan(task))
        if rule_plan.status != "unsupported_task":
            return rule_plan

        try:
            preplan = await self.preplan_service.build(task)
        except Exception:
            return self._unsupported(task, "preplan")

        planner_result = await self.planner_service.build(task, preplan)
        return self._normalize_planner_output(task, planner_result)

    def plan_sync(self, task: TaskSpec) -> PlanBundle:
        rule_plan = self._normalize_rule_plan(task, self.rule_planner.plan_sync(task))
        if rule_plan.status != "unsupported_task":
            return rule_plan

        try:
            preplan = self.preplan_service.build_sync(task)
        except Exception:
            return self._unsupported(task, "preplan")

        planner_result = self.planner_service.build_sync(task, preplan)
        return self._normalize_planner_output(task, planner_result)
