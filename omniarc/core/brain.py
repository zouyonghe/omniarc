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
        steps = plan.get("steps", [])
        index = max(state.current_step - 1, 0)
        current_step = (
            steps[min(index, len(steps) - 1)]
            if steps
            else {"kind": "done", "params": {}}
        )
        return Decision(
            step_evaluation="success",
            reasoning=(
                f"Executing planner step {state.current_step}: "
                f"{current_step['kind']}"
            ),
            next_goal=task.task,
            planned_action=current_step,
        )
