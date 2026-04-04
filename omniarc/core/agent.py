from __future__ import annotations

from omniarc.core.actor import Actor
from omniarc.core.brain import Brain
from omniarc.core.composite_planner import CompositePlanner
from omniarc.core.memory import Memory
from omniarc.core.recovery import RecoveryCoordinator
from omniarc.core.verifier import StepVerifier
from omniarc.core.models import Decision
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
        verifier: StepVerifier,
        recovery: RecoveryCoordinator,
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
        self.verifier = verifier
        self.recovery = recovery
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
        planner=None,
        task: TaskSpec,
        state: RunState | None = None,
        should_pause=None,
    ) -> "OmniArcAgent":
        return cls(
            observer=observer,
            executor=executor,
            planner=planner or CompositePlanner(),
            brain=Brain(),
            actor=Actor(),
            memory=Memory(),
            verifier=StepVerifier(),
            recovery=RecoveryCoordinator(),
            task=task,
            state=state,
            should_pause=should_pause,
        )

    def _fail_unsupported_plan(self) -> RunState:
        self.state.last_decision = Decision(
            step_evaluation="unsupported_task",
            reasoning="Task is not supported by the current planner",
            next_goal=self.task.task,
            planned_action={},
        )
        self.state.status = "failed"
        return self.state

    async def run(self, max_steps: int = 100) -> RunState:
        self.state.status = "planning"
        plan = await self.planner.plan(self.task)
        if plan.get("status") == "unsupported_task":
            return self._fail_unsupported_plan()
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
            if not actions:
                self.state.status = "failed"
                return self.state
            self.state.action_history.extend(actions)

            self.state.status = "acting"
            results = await self.executor.execute(actions)
            self.state.last_results = results
            if any(not result.success for result in results):
                self.state.status = "failed"
                return self.state

            after_observation = await self.observer.observe()
            verification = self.verifier.verify(
                task_text=self.task.task,
                actions=actions,
                before=observation,
                after=after_observation,
            )
            self.state.last_observation = after_observation
            self.state.last_verification = verification

            self.state.status = "recording"
            await self.memory.record(
                self.state, after_observation, decision, actions, results
            )

            if verification.status == "complete":
                self.state.is_done = True
                self.state.status = "completed"
                return self.state

            if verification.status == "progress":
                self.state.action_retry_count = 0
                self.state.strategy_retry_count = 0

            if verification.failure_category is not None:
                recovery = self.recovery.decide(self.state, verification)
                if recovery.action == "fail":
                    self.state.status = "failed"
                    return self.state
                if recovery.action == "action_retry":
                    if self.should_pause and self.should_pause():
                        self.state.status = "paused"
                        return self.state
                    continue
                if recovery.action in {"strategy_retry", "replan"}:
                    self.state.action_retry_count = 0
                    self.state.status = "planning"
                    plan = await self.planner.plan(self.task)
                    if plan.get("status") == "unsupported_task":
                        return self._fail_unsupported_plan()
                    self.state.plan_step_index = 0
                    if self.should_pause and self.should_pause():
                        self.state.status = "paused"
                        return self.state
                    continue

            if self.should_pause and self.should_pause():
                self.state.status = "paused"
                return self.state

            self.state.plan_step_index += 1

        self.state.status = "failed"
        return self.state
