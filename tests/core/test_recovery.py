from __future__ import annotations

from omniarc.core.models import VerificationResult
from omniarc.core.recovery import RecoveryCoordinator
from omniarc.core.state import RunState


def test_recovery_uses_strategy_retry_for_wrong_app() -> None:
    coordinator = RecoveryCoordinator()
    state = RunState()

    decision = coordinator.decide(
        state,
        VerificationResult(
            status="wrong_app",
            failure_category="wrong_app",
            evidence={"actual_app": "Codex"},
        ),
    )

    assert decision.action == "strategy_retry"
    assert decision.failure_category == "wrong_app"


def test_recovery_requests_replan_after_wrong_app_strategy_budget_is_exhausted() -> (
    None
):
    coordinator = RecoveryCoordinator(strategy_retry_budget=1)
    state = RunState()

    first = coordinator.decide(
        state,
        VerificationResult(
            status="wrong_app",
            failure_category="wrong_app",
            evidence={"actual_app": "Codex"},
        ),
    )
    second = coordinator.decide(
        state,
        VerificationResult(
            status="wrong_app",
            failure_category="wrong_app",
            evidence={"actual_app": "Codex"},
        ),
    )

    assert first.action == "strategy_retry"
    assert second.action == "replan"
    assert second.failure_category == "wrong_app"


def test_recovery_uses_action_retry_then_strategy_retry_for_no_visible_change() -> None:
    coordinator = RecoveryCoordinator(action_retry_budget=1)
    state = RunState()

    first = coordinator.decide(
        state,
        VerificationResult(
            status="no_visible_change",
            failure_category="no_visible_change",
            evidence={},
        ),
    )
    second = coordinator.decide(
        state,
        VerificationResult(
            status="no_visible_change",
            failure_category="no_visible_change",
            evidence={},
        ),
    )

    assert first.action == "action_retry"
    assert second.action == "strategy_retry"


def test_recovery_requests_replan_after_local_retry_budgets_are_exhausted() -> None:
    coordinator = RecoveryCoordinator(action_retry_budget=1, strategy_retry_budget=1)
    state = RunState()

    outcomes = [
        coordinator.decide(
            state,
            VerificationResult(
                status="no_visible_change",
                failure_category="no_visible_change",
                evidence={},
            ),
        )
        for _ in range(3)
    ]

    assert [outcome.action for outcome in outcomes] == [
        "action_retry",
        "strategy_retry",
        "replan",
    ]
    assert outcomes[-1].failure_category == "no_visible_change"
