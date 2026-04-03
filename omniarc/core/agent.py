from __future__ import annotations

from omniarc.core.actor import Actor
from omniarc.core.brain import Brain
from omniarc.core.memory import Memory
from omniarc.core.models import ActionResult, TaskSpec
from omniarc.core.planner import Planner
from omniarc.core.state import RunState


class OmniArcAgent:
    def __init__(
        self,
        *,
        observer,
        executor,
        planner: Planner,
        brain: Brain,
        actor: Actor,
        memory: Memory,
        task: TaskSpec,
        state: RunState | None = None,
        should_pause=None,
    ) -> None:
        self.observer = observer
        self.executor = executor
        self.planner = planner
        self.brain = brain
        self.actor = actor
        self.memory = memory
        self.task = task
        self.state = state or RunState()
        self.should_pause = should_pause

    @staticmethod
    def default_test_results() -> list[ActionResult]:
        return [ActionResult(success=True, is_done=True)]

    @classmethod
    def build_for_test(
        cls,
        *,
        observer,
        executor,
        task: TaskSpec,
        state: RunState | None = None,
        should_pause=None,
    ) -> "OmniArcAgent":
        return cls(
            observer=observer,
            executor=executor,
            planner=Planner(),
            brain=Brain(),
            actor=Actor(),
            memory=Memory(),
            task=task,
            state=state,
            should_pause=should_pause,
        )

    async def run(self, max_steps: int = 100) -> RunState:
        self.state.status = "planning"
        plan = await self.planner.plan(self.task)
        starting_step = self.state.current_step

        for step in range(starting_step + 1, starting_step + max_steps + 1):
            self.state.current_step = step

            self.state.status = "observing"
            observation = await self.observer.observe()
            self.state.last_observation = observation

            self.state.status = "deciding"
            decision = await self.brain.decide(self.task, observation, plan, self.state)
            self.state.last_decision = decision

            actions = await self.actor.act(decision)
            self.state.last_actions = actions
            self.state.action_history.extend(actions)

            self.state.status = "acting"
            results = await self.executor.execute(actions)
            self.state.last_results = results

            self.state.status = "recording"
            await self.memory.record(
                self.state, observation, decision, actions, results
            )

            if self.should_pause and self.should_pause():
                self.state.status = "paused"
                return self.state

            if any(result.is_done for result in results):
                self.state.is_done = True
                self.state.status = "completed"
                return self.state

        self.state.status = "failed"
        return self.state
