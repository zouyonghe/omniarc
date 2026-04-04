from __future__ import annotations

from typing import Any

from omniarc.core.models import Decision, Observation, TaskSpec
from omniarc.core.state import RunState


class Brain:
    async def decide(
        self,
        task: TaskSpec,
        observation: Observation,
        plan: dict[str, Any],
        state: RunState,
    ) -> Decision:
        if plan.get("status") == "unsupported_task":
            return Decision(
                step_evaluation="unsupported_task",
                reasoning="Task is not supported by the current planner",
                next_goal=task.task,
                planned_action={},
            )
        steps = plan.get("steps", [])
        index = max(state.plan_step_index, 0)
        current_step = (
            steps[min(index, len(steps) - 1)]
            if steps
            else {"kind": "done", "params": {}}
        )
        return Decision(
            step_evaluation="success",
            reasoning=(
                f"Executing planner step {state.plan_step_index + 1}: {current_step['kind']}"
            ),
            next_goal=task.task,
            planned_action=current_step,
        )
