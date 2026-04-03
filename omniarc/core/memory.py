from __future__ import annotations

from omniarc.core.models import Action, ActionResult, Decision, MemoryEntry, Observation
from omniarc.core.state import RunState


class Memory:
    async def record(
        self,
        state: RunState,
        observation: Observation,
        decision: Decision,
        actions: list[Action],
        results: list[ActionResult],
    ) -> None:
        state.memory.append(
            MemoryEntry(
                content=decision.reasoning or decision.next_goal or "step recorded",
                step=state.current_step,
            )
        )
