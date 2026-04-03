from __future__ import annotations

from omniarc.core.models import Action, Decision


class Actor:
    async def act(self, decision: Decision) -> list[Action]:
        if decision.planned_action:
            return [
                Action(
                    kind=decision.planned_action["kind"],
                    params=decision.planned_action.get("params", {}),
                )
            ]
        if not decision.next_goal:
            return [Action(kind="wait")]
        return [Action(kind="done")]
