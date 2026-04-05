from __future__ import annotations

import pytest

from omniarc.core.actor import Actor
from omniarc.core.agent import OmniArcAgent
from omniarc.core.brain import Brain
from omniarc.core.recovery import RecoveryCoordinator
from omniarc.core.models import (
    ActionResult,
    Decision,
    Observation,
    PlanBundle,
    PlanStep,
    RecoveryDecision,
    TaskSpec,
    VerificationResult,
)
from omniarc.core.state import RunState


class FakeObserver:
    def __init__(self, observations: list[Observation]) -> None:
        self._observations = observations
        self.calls = 0

    async def observe(self) -> Observation:
        index = min(self.calls, len(self._observations) - 1)
        self.calls += 1
        return self._observations[index]


class FakeExecutor:
    def __init__(self, results: list[list[ActionResult]]) -> None:
        self._results = results
        self.calls = 0
        self.executed_action_kinds: list[str] = []

    async def execute(self, actions):
        index = min(self.calls, len(self._results) - 1)
        self.calls += 1
        self.executed_action_kinds.extend(action.kind for action in actions)
        return self._results[index]


class FakeMemory:
    def __init__(self) -> None:
        self.records: list[tuple] = []

    async def record(self, state, observation, decision, actions, results) -> None:
        self.records.append((state.status, decision.step_evaluation, actions, results))


class StaticPlanner:
    def __init__(self, plan) -> None:
        self._plan = plan

    async def plan(self, task: TaskSpec):
        return self._plan


class SequencedPlanner:
    def __init__(self, plans: list) -> None:
        self.plans = plans
        self.calls = 0

    async def plan(self, task: TaskSpec):
        index = min(self.calls, len(self.plans) - 1)
        self.calls += 1
        return self.plans[index]


class StaticVerifier:
    def __init__(self, outcomes: list[VerificationResult]) -> None:
        self.outcomes = outcomes
        self.calls = 0

    def verify(self, *, task_text, actions, before, after):
        index = min(self.calls, len(self.outcomes) - 1)
        self.calls += 1
        return self.outcomes[index]


class StaticRecovery:
    def __init__(self, decisions: list[RecoveryDecision]) -> None:
        self.decisions = decisions
        self.calls = 0

    def decide(
        self, state: RunState, verification: VerificationResult
    ) -> RecoveryDecision:
        index = min(self.calls, len(self.decisions) - 1)
        self.calls += 1
        decision = self.decisions[index]
        state.last_recovery = decision
        return decision


def _plan_bundle(*steps: PlanStep, summary: str = "test plan") -> PlanBundle:
    return PlanBundle(
        summary=summary, status="supported", source="planner", steps=list(steps)
    )


@pytest.mark.asyncio
async def test_agent_reaches_completed_state_when_verifier_confirms_completion() -> (
    None
):
    agent = OmniArcAgent(
        observer=FakeObserver(
            [Observation(screenshot_path="after.png", active_app="Finder")]
        ),
        executor=FakeExecutor([[ActionResult(success=True, is_done=True)]]),
        planner=StaticPlanner(
            {"status": "supported", "steps": [{"kind": "done", "params": {}}]}
        ),
        brain=Brain(),
        actor=Actor(),
        memory=FakeMemory(),
        verifier=StaticVerifier(
            [VerificationResult(status="complete", evidence={"matched_text": "Finder"})]
        ),
        recovery=StaticRecovery([]),
        task=TaskSpec(task="Open Finder"),
    )

    status = await agent.run(max_steps=1)

    assert status.status == "completed"
    assert status.last_verification is not None
    assert status.last_verification.status == "complete"


@pytest.mark.asyncio
async def test_agent_advances_plan_step_only_after_subgoal_completion() -> None:
    executor = FakeExecutor(
        [
            [ActionResult(success=True, is_done=False)],
            [ActionResult(success=True, is_done=False)],
            [ActionResult(success=True, is_done=True)],
        ]
    )
    agent = OmniArcAgent(
        observer=FakeObserver(
            [
                Observation(screenshot_path="1.png", active_app="Finder"),
                Observation(screenshot_path="2.png", active_app="Finder"),
                Observation(screenshot_path="3.png", active_app="Finder"),
                Observation(screenshot_path="4.png", active_app="Finder"),
                Observation(screenshot_path="5.png", active_app="Finder"),
                Observation(screenshot_path="6.png", active_app="Finder"),
            ]
        ),
        executor=executor,
        planner=StaticPlanner(
            _plan_bundle(
                PlanStep(
                    goal="Open Finder",
                    completion_hint="Finder is frontmost",
                    allowed_actions=["open_app"],
                    planned_action={"kind": "open_app", "params": {"name": "Finder"}},
                ),
                PlanStep(
                    goal="Confirm Finder is ready",
                    completion_hint="Task is complete",
                    allowed_actions=["done"],
                    planned_action={"kind": "done", "params": {}},
                ),
            )
        ),
        brain=Brain(),
        actor=Actor(),
        memory=FakeMemory(),
        verifier=StaticVerifier(
            [
                VerificationResult(
                    status="progress", evidence={"matched_app": "Finder"}
                ),
                VerificationResult(
                    status="step_complete", evidence={"matched_app": "Finder"}
                ),
                VerificationResult(
                    status="complete", evidence={"matched_app": "Finder"}
                ),
            ]
        ),
        recovery=StaticRecovery([]),
        task=TaskSpec(task="Open Finder"),
    )

    status = await agent.run(max_steps=3)

    assert status.status == "completed"
    assert status.plan_step_index == 1
    assert executor.executed_action_kinds == ["open_app", "open_app", "done"]


@pytest.mark.asyncio
async def test_agent_strategy_retry_stays_within_same_subgoal() -> None:
    planner = SequencedPlanner(
        [
            _plan_bundle(
                PlanStep(
                    goal="Open Finder",
                    completion_hint="Finder is frontmost",
                    allowed_actions=["open_app"],
                    planned_action={"kind": "open_app", "params": {"name": "Finder"}},
                ),
                PlanStep(
                    goal="Finish task",
                    completion_hint="Task is complete",
                    allowed_actions=["done"],
                    planned_action={"kind": "done", "params": {}},
                ),
            )
        ]
    )
    executor = FakeExecutor(
        [
            [ActionResult(success=True, is_done=False)],
            [ActionResult(success=True, is_done=False)],
            [ActionResult(success=True, is_done=True)],
        ]
    )
    agent = OmniArcAgent(
        observer=FakeObserver(
            [
                Observation(screenshot_path="1.png", active_app="Finder"),
                Observation(screenshot_path="2.png", active_app="Finder"),
                Observation(screenshot_path="3.png", active_app="Finder"),
                Observation(screenshot_path="4.png", active_app="Finder"),
                Observation(screenshot_path="5.png", active_app="Finder"),
                Observation(screenshot_path="6.png", active_app="Finder"),
            ]
        ),
        executor=executor,
        planner=planner,
        brain=Brain(),
        actor=Actor(),
        memory=FakeMemory(),
        verifier=StaticVerifier(
            [
                VerificationResult(
                    status="no_visible_change",
                    failure_category="no_visible_change",
                    evidence={},
                ),
                VerificationResult(
                    status="step_complete", evidence={"matched_app": "Finder"}
                ),
                VerificationResult(
                    status="complete", evidence={"matched_app": "Finder"}
                ),
            ]
        ),
        recovery=StaticRecovery(
            [
                RecoveryDecision(
                    action="strategy_retry",
                    failure_category="no_visible_change",
                    reason="try the same subgoal again",
                )
            ]
        ),
        task=TaskSpec(task="Open Finder"),
    )

    status = await agent.run(max_steps=3)

    assert status.status == "completed"
    assert planner.calls == 1
    assert executor.executed_action_kinds == ["open_app", "open_app", "done"]


@pytest.mark.asyncio
async def test_agent_fails_unsupported_task_without_executing_actions() -> None:
    executor = FakeExecutor([[ActionResult(success=True, is_done=True)]])
    agent = OmniArcAgent(
        observer=FakeObserver(
            [Observation(screenshot_path="after.png", active_app="Codex")]
        ),
        executor=executor,
        planner=StaticPlanner({"status": "unsupported_task", "steps": []}),
        brain=Brain(),
        actor=Actor(),
        memory=FakeMemory(),
        verifier=StaticVerifier([]),
        recovery=StaticRecovery([]),
        task=TaskSpec(task="Do one thing"),
    )

    status = await agent.run(max_steps=1)

    assert status.status == "failed"
    assert status.last_actions == []
    assert executor.calls == 0
    assert status.last_decision is not None
    assert status.last_decision.step_evaluation == "unsupported_task"


@pytest.mark.asyncio
async def test_agent_uses_recovery_when_verifier_reports_no_visible_change() -> None:
    agent = OmniArcAgent(
        observer=FakeObserver(
            [
                Observation(screenshot_path="step-1.png", active_app="Safari"),
                Observation(screenshot_path="step-2.png", active_app="Safari"),
            ]
        ),
        executor=FakeExecutor(
            [
                [ActionResult(success=True, is_done=False)],
                [ActionResult(success=True, is_done=True)],
            ]
        ),
        planner=StaticPlanner(
            {"status": "supported", "steps": [{"kind": "scroll", "params": {}}]}
        ),
        brain=Brain(),
        actor=Actor(),
        memory=FakeMemory(),
        verifier=StaticVerifier(
            [
                VerificationResult(
                    status="no_visible_change",
                    failure_category="no_visible_change",
                    evidence={},
                ),
                VerificationResult(
                    status="complete", evidence={"matched_text": "Done"}
                ),
            ]
        ),
        recovery=StaticRecovery(
            [
                RecoveryDecision(
                    action="action_retry",
                    failure_category="no_visible_change",
                    reason="retry same action",
                )
            ]
        ),
        task=TaskSpec(task="Open Safari and scroll down"),
    )

    status = await agent.run(max_steps=2)

    assert status.status == "completed"
    assert status.last_recovery is not None
    assert status.last_recovery.action == "action_retry"


@pytest.mark.asyncio
async def test_agent_does_not_complete_when_done_action_lacks_verifier_evidence() -> (
    None
):
    agent = OmniArcAgent(
        observer=FakeObserver(
            [Observation(screenshot_path="after.png", active_app="Finder")]
        ),
        executor=FakeExecutor([[ActionResult(success=True, is_done=True)]]),
        planner=StaticPlanner(
            {"status": "supported", "steps": [{"kind": "done", "params": {}}]}
        ),
        brain=Brain(),
        actor=Actor(),
        memory=FakeMemory(),
        verifier=StaticVerifier(
            [
                VerificationResult(
                    status="no_visible_change",
                    failure_category="no_visible_change",
                    evidence={},
                )
            ]
        ),
        recovery=StaticRecovery(
            [
                RecoveryDecision(
                    action="fail",
                    failure_category="retry_budget_exhausted",
                    reason="no evidence of completion",
                )
            ]
        ),
        task=TaskSpec(task="Open Finder"),
    )

    status = await agent.run(max_steps=1)

    assert status.status == "failed"
    assert status.last_verification is not None
    assert status.last_verification.status == "no_visible_change"


@pytest.mark.asyncio
async def test_agent_retries_same_step_instead_of_advancing_after_failed_verification() -> (
    None
):
    executor = FakeExecutor(
        [
            [ActionResult(success=True, is_done=False)],
            [ActionResult(success=True, is_done=False)],
        ]
    )
    agent = OmniArcAgent(
        observer=FakeObserver(
            [
                Observation(screenshot_path="step-1.png", active_app="Finder"),
                Observation(screenshot_path="step-2.png", active_app="Finder"),
                Observation(screenshot_path="step-3.png", active_app="Finder"),
                Observation(screenshot_path="step-4.png", active_app="Finder"),
            ]
        ),
        executor=executor,
        planner=StaticPlanner(
            {
                "status": "supported",
                "steps": [
                    {"kind": "open_app", "params": {"name": "Finder"}},
                    {"kind": "done", "params": {}},
                ],
            }
        ),
        brain=Brain(),
        actor=Actor(),
        memory=FakeMemory(),
        verifier=StaticVerifier(
            [
                VerificationResult(
                    status="no_visible_change",
                    failure_category="no_visible_change",
                    evidence={},
                ),
                VerificationResult(
                    status="no_visible_change",
                    failure_category="no_visible_change",
                    evidence={},
                ),
            ]
        ),
        recovery=StaticRecovery(
            [
                RecoveryDecision(
                    action="action_retry",
                    failure_category="no_visible_change",
                    reason="retry same action",
                ),
                RecoveryDecision(
                    action="fail",
                    failure_category="retry_budget_exhausted",
                    reason="give up",
                ),
            ]
        ),
        task=TaskSpec(task="Open Finder"),
    )

    status = await agent.run(max_steps=2)

    assert status.status == "failed"
    assert executor.executed_action_kinds == ["open_app", "open_app"]


@pytest.mark.asyncio
async def test_agent_resets_retry_budgets_after_verified_progress() -> None:
    executor = FakeExecutor(
        [
            [ActionResult(success=True, is_done=False)],
            [ActionResult(success=True, is_done=False)],
            [ActionResult(success=True, is_done=True)],
        ]
    )
    state = RunState(action_retry_count=1, strategy_retry_count=1)
    agent = OmniArcAgent(
        observer=FakeObserver(
            [
                Observation(screenshot_path="step-1.png", active_app="Finder"),
                Observation(screenshot_path="step-2.png", active_app="Finder"),
                Observation(screenshot_path="step-3.png", active_app="Finder"),
                Observation(screenshot_path="step-4.png", active_app="Finder"),
                Observation(screenshot_path="step-5.png", active_app="Finder"),
                Observation(screenshot_path="step-6.png", active_app="Finder"),
            ]
        ),
        executor=executor,
        planner=StaticPlanner(
            {
                "status": "supported",
                "steps": [
                    {"kind": "open_app", "params": {"name": "Finder"}},
                    {"kind": "done", "params": {}},
                ],
            }
        ),
        brain=Brain(),
        actor=Actor(),
        memory=FakeMemory(),
        verifier=StaticVerifier(
            [
                VerificationResult(
                    status="progress", evidence={"matched_app": "Finder"}
                ),
                VerificationResult(
                    status="no_visible_change",
                    failure_category="no_visible_change",
                    evidence={},
                ),
                VerificationResult(
                    status="complete", evidence={"matched_app": "Finder"}
                ),
            ]
        ),
        recovery=RecoveryCoordinator(action_retry_budget=1, strategy_retry_budget=1),
        task=TaskSpec(task="Open Finder"),
        state=state,
    )

    status = await agent.run(max_steps=3)

    assert status.status == "completed"
    assert status.last_recovery is not None
    assert status.last_recovery.action == "action_retry"


@pytest.mark.asyncio
async def test_agent_replans_when_recovery_requests_replan() -> None:
    planner = SequencedPlanner(
        [
            {
                "status": "supported",
                "steps": [{"kind": "open_app", "params": {"name": "Safari"}}],
            },
            {"status": "supported", "steps": [{"kind": "done", "params": {}}]},
        ]
    )
    executor = FakeExecutor(
        [
            [ActionResult(success=True, is_done=False)],
            [ActionResult(success=True, is_done=True)],
        ]
    )
    agent = OmniArcAgent(
        observer=FakeObserver(
            [
                Observation(screenshot_path="step-1.png", active_app="Codex"),
                Observation(screenshot_path="step-2.png", active_app="Codex"),
                Observation(screenshot_path="step-3.png", active_app="Safari"),
                Observation(screenshot_path="step-4.png", active_app="Safari"),
            ]
        ),
        executor=executor,
        planner=planner,
        brain=Brain(),
        actor=Actor(),
        memory=FakeMemory(),
        verifier=StaticVerifier(
            [
                VerificationResult(
                    status="wrong_app",
                    failure_category="wrong_app",
                    evidence={"actual_app": "Codex"},
                ),
                VerificationResult(
                    status="complete", evidence={"matched_app": "Safari"}
                ),
            ]
        ),
        recovery=StaticRecovery(
            [
                RecoveryDecision(
                    action="replan",
                    failure_category="wrong_app",
                    reason="switch strategy via replan",
                )
            ]
        ),
        task=TaskSpec(task="Open Safari"),
    )

    status = await agent.run(max_steps=2)

    assert status.status == "completed"
    assert planner.calls == 2
    assert executor.executed_action_kinds == ["open_app", "done"]


@pytest.mark.asyncio
async def test_agent_replan_restarts_from_first_subgoal_of_replacement_bundle() -> None:
    planner = SequencedPlanner(
        [
            _plan_bundle(
                PlanStep(
                    goal="Open Finder",
                    completion_hint="Finder is frontmost",
                    allowed_actions=["open_app"],
                    planned_action={"kind": "open_app", "params": {"name": "Finder"}},
                ),
                PlanStep(
                    goal="Finish Finder task",
                    completion_hint="Finder task is complete",
                    allowed_actions=["done"],
                    planned_action={"kind": "done", "params": {}},
                ),
            ),
            _plan_bundle(
                PlanStep(
                    goal="Open Safari",
                    completion_hint="Safari is frontmost",
                    allowed_actions=["open_app"],
                    planned_action={"kind": "open_app", "params": {"name": "Safari"}},
                ),
                PlanStep(
                    goal="Finish Safari task",
                    completion_hint="Safari task is complete",
                    allowed_actions=["done"],
                    planned_action={"kind": "done", "params": {}},
                ),
            ),
        ]
    )
    executor = FakeExecutor(
        [
            [ActionResult(success=True, is_done=False)],
            [ActionResult(success=True, is_done=False)],
            [ActionResult(success=True, is_done=False)],
            [ActionResult(success=True, is_done=True)],
        ]
    )
    agent = OmniArcAgent(
        observer=FakeObserver(
            [
                Observation(screenshot_path="1.png", active_app="Finder"),
                Observation(screenshot_path="2.png", active_app="Finder"),
                Observation(screenshot_path="3.png", active_app="Finder"),
                Observation(screenshot_path="4.png", active_app="Finder"),
                Observation(screenshot_path="5.png", active_app="Safari"),
                Observation(screenshot_path="6.png", active_app="Safari"),
                Observation(screenshot_path="7.png", active_app="Safari"),
                Observation(screenshot_path="8.png", active_app="Safari"),
            ]
        ),
        executor=executor,
        planner=planner,
        brain=Brain(),
        actor=Actor(),
        memory=FakeMemory(),
        verifier=StaticVerifier(
            [
                VerificationResult(
                    status="step_complete", evidence={"matched_app": "Finder"}
                ),
                VerificationResult(
                    status="no_visible_change",
                    failure_category="no_visible_change",
                    evidence={},
                ),
                VerificationResult(
                    status="step_complete", evidence={"matched_app": "Safari"}
                ),
                VerificationResult(
                    status="complete", evidence={"matched_app": "Safari"}
                ),
            ]
        ),
        recovery=StaticRecovery(
            [
                RecoveryDecision(
                    action="replan",
                    failure_category="no_visible_change",
                    reason="stalled subgoal",
                )
            ]
        ),
        task=TaskSpec(task="Open Finder then Safari"),
    )

    status = await agent.run(max_steps=4)

    assert status.status == "completed"
    assert planner.calls == 2
    assert status.replan_count == 1
    assert executor.executed_action_kinds == ["open_app", "done", "open_app", "done"]


@pytest.mark.asyncio
async def test_agent_fails_when_replan_budget_is_exhausted() -> None:
    planner = SequencedPlanner(
        [
            _plan_bundle(
                PlanStep(
                    goal="Open Finder",
                    completion_hint="Finder is frontmost",
                    allowed_actions=["open_app"],
                    planned_action={"kind": "open_app", "params": {"name": "Finder"}},
                )
            )
        ]
    )
    agent = OmniArcAgent(
        observer=FakeObserver(
            [
                Observation(screenshot_path="1.png", active_app="Finder"),
                Observation(screenshot_path="2.png", active_app="Finder"),
            ]
        ),
        executor=FakeExecutor([[ActionResult(success=True, is_done=False)]]),
        planner=planner,
        brain=Brain(),
        actor=Actor(),
        memory=FakeMemory(),
        verifier=StaticVerifier(
            [
                VerificationResult(
                    status="no_visible_change",
                    failure_category="no_visible_change",
                    evidence={},
                )
            ]
        ),
        recovery=StaticRecovery(
            [
                RecoveryDecision(
                    action="replan",
                    failure_category="no_visible_change",
                    reason="stalled subgoal",
                )
            ]
        ),
        task=TaskSpec(task="Open Finder"),
        state=RunState(replan_count=1),
        max_replans=1,
    )

    status = await agent.run(max_steps=1)

    assert status.status == "failed"
    assert status.last_recovery is not None
    assert status.last_recovery.failure_category == "replan_budget_exhausted"
    assert planner.calls == 1


@pytest.mark.asyncio
async def test_agent_replan_restarts_from_first_step_and_resets_retry_window() -> None:
    planner = SequencedPlanner(
        [
            {
                "status": "supported",
                "steps": [
                    {"kind": "open_app", "params": {"name": "Finder"}},
                    {"kind": "done", "params": {}},
                ],
            },
            {
                "status": "supported",
                "steps": [
                    {"kind": "open_app", "params": {"name": "Safari"}},
                    {"kind": "done", "params": {}},
                ],
            },
        ]
    )
    executor = FakeExecutor(
        [
            [ActionResult(success=True, is_done=False)],
            [ActionResult(success=True, is_done=False)],
            [ActionResult(success=True, is_done=False)],
            [ActionResult(success=True, is_done=False)],
            [ActionResult(success=True, is_done=False)],
            [ActionResult(success=True, is_done=True)],
        ]
    )
    agent = OmniArcAgent(
        observer=FakeObserver(
            [
                Observation(screenshot_path="1.png", active_app="Finder"),
                Observation(screenshot_path="2.png", active_app="Finder"),
                Observation(screenshot_path="3.png", active_app="Finder"),
                Observation(screenshot_path="4.png", active_app="Finder"),
                Observation(screenshot_path="5.png", active_app="Finder"),
                Observation(screenshot_path="6.png", active_app="Safari"),
                Observation(screenshot_path="7.png", active_app="Safari"),
                Observation(screenshot_path="8.png", active_app="Safari"),
                Observation(screenshot_path="9.png", active_app="Safari"),
                Observation(screenshot_path="10.png", active_app="Safari"),
            ]
        ),
        executor=executor,
        planner=planner,
        brain=Brain(),
        actor=Actor(),
        memory=FakeMemory(),
        verifier=StaticVerifier(
            [
                VerificationResult(
                    status="progress", evidence={"matched_app": "Finder"}
                ),
                VerificationResult(
                    status="no_visible_change",
                    failure_category="no_visible_change",
                    evidence={},
                ),
                VerificationResult(
                    status="no_visible_change",
                    failure_category="no_visible_change",
                    evidence={},
                ),
                VerificationResult(
                    status="no_visible_change",
                    failure_category="no_visible_change",
                    evidence={},
                ),
                VerificationResult(
                    status="no_visible_change",
                    failure_category="no_visible_change",
                    evidence={},
                ),
                VerificationResult(
                    status="complete", evidence={"matched_app": "Safari"}
                ),
            ]
        ),
        recovery=RecoveryCoordinator(action_retry_budget=1, strategy_retry_budget=1),
        task=TaskSpec(task="Open Finder then Safari"),
    )

    status = await agent.run(max_steps=6)

    assert status.status == "completed"
    assert planner.calls == 2
    assert executor.executed_action_kinds == [
        "open_app",
        "open_app",
        "open_app",
        "open_app",
        "open_app",
        "open_app",
    ]


@pytest.mark.asyncio
async def test_agent_fails_immediately_when_replan_returns_unsupported_task() -> None:
    planner = SequencedPlanner(
        [
            {
                "status": "supported",
                "steps": [{"kind": "open_app", "params": {"name": "Safari"}}],
            },
            {"status": "unsupported_task", "steps": []},
        ]
    )
    executor = FakeExecutor([[ActionResult(success=True, is_done=False)]])
    agent = OmniArcAgent(
        observer=FakeObserver(
            [
                Observation(screenshot_path="step-1.png", active_app="Codex"),
                Observation(screenshot_path="step-2.png", active_app="Codex"),
            ]
        ),
        executor=executor,
        planner=planner,
        brain=Brain(),
        actor=Actor(),
        memory=FakeMemory(),
        verifier=StaticVerifier(
            [
                VerificationResult(
                    status="wrong_app",
                    failure_category="wrong_app",
                    evidence={"actual_app": "Codex"},
                )
            ]
        ),
        recovery=StaticRecovery(
            [
                RecoveryDecision(
                    action="replan",
                    failure_category="wrong_app",
                    reason="switch strategy via replan",
                )
            ]
        ),
        task=TaskSpec(task="Open Safari"),
    )

    status = await agent.run(max_steps=2)

    assert status.status == "failed"
    assert executor.executed_action_kinds == ["open_app"]


@pytest.mark.asyncio
async def test_agent_fails_fast_when_executor_returns_error_result() -> None:
    agent = OmniArcAgent(
        observer=FakeObserver(
            [Observation(screenshot_path="after.png", active_app="Finder")]
        ),
        executor=FakeExecutor(
            [
                [
                    ActionResult(
                        success=False,
                        error_type="runtime_error",
                        error_message="open app failed",
                    )
                ]
            ]
        ),
        planner=StaticPlanner(
            {
                "status": "supported",
                "steps": [{"kind": "open_app", "params": {"name": "Finder"}}],
            }
        ),
        brain=Brain(),
        actor=Actor(),
        memory=FakeMemory(),
        verifier=StaticVerifier([VerificationResult(status="progress", evidence={})]),
        recovery=StaticRecovery([]),
        task=TaskSpec(task="Open Finder"),
    )

    status = await agent.run(max_steps=1)

    assert status.status == "failed"
    assert status.last_results[0].success is False
