from __future__ import annotations

from typing import Any

from omniarc.core.models import Decision, Observation, PlanBundle, PlanStep, TaskSpec
from omniarc.core.state import RunState


def _plan_status(plan: dict[str, Any] | PlanBundle) -> str:
    return plan.status if isinstance(plan, PlanBundle) else str(plan.get("status"))


def _plan_steps(plan: dict[str, Any] | PlanBundle) -> list[Any]:
    return plan.steps if isinstance(plan, PlanBundle) else plan.get("steps", [])


def _action_from_plan_step(step: PlanStep) -> dict[str, Any]:
    if step.planned_action:
        return dict(step.planned_action)
    action_kind = step.allowed_actions[0] if step.allowed_actions else "done"
    return {"kind": action_kind, "params": {}}


class Brain:
    async def decide(
        self,
        task: TaskSpec,
        observation: Observation,
        plan: dict[str, Any] | PlanBundle,
        state: RunState,
    ) -> Decision:
        if _plan_status(plan) == "unsupported_task":
            return Decision(
                step_evaluation="unsupported_task",
                reasoning="Task is not supported by the current planner",
                next_goal=task.task,
                planned_action={},
            )
        steps = _plan_steps(plan)
        index = max(state.plan_step_index, 0)
        current_step = steps[min(index, len(steps) - 1)] if steps else None
        planned_action = (
            _action_from_plan_step(current_step)
            if isinstance(current_step, PlanStep)
            else current_step or {"kind": "done", "params": {}}
        )
        step_name = (
            current_step.goal
            if isinstance(current_step, PlanStep)
            else planned_action.get("kind", "done")
        )
        return Decision(
            step_evaluation="success",
            reasoning=f"Executing planner step {state.plan_step_index + 1}: {step_name}",
            next_goal=task.task,
            planned_action=planned_action,
        )
