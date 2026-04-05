from __future__ import annotations

from omniarc.core.models import RecoveryDecision, VerificationResult
from omniarc.core.state import RunState


class RecoveryCoordinator:
    def __init__(
        self, *, action_retry_budget: int = 1, strategy_retry_budget: int = 1
    ) -> None:
        self.action_retry_budget = action_retry_budget
        self.strategy_retry_budget = strategy_retry_budget

    def decide(
        self, state: RunState, verification: VerificationResult
    ) -> RecoveryDecision:
        if verification.failure_category == "wrong_app":
            if state.strategy_retry_count >= self.strategy_retry_budget:
                decision = RecoveryDecision(
                    action="replan",
                    failure_category="wrong_app",
                    reason="local recovery is exhausted for wrong_app failures",
                )
                state.last_recovery = decision
                return decision
            state.strategy_retry_count += 1
            decision = RecoveryDecision(
                action="strategy_retry",
                failure_category="wrong_app",
                reason="frontmost app did not match the expected target",
            )
            state.last_recovery = decision
            return decision

        if verification.failure_category == "no_visible_change":
            if state.action_retry_count < self.action_retry_budget:
                state.action_retry_count += 1
                decision = RecoveryDecision(
                    action="action_retry",
                    failure_category="no_visible_change",
                    reason="observation did not change after the last action",
                )
                state.last_recovery = decision
                return decision
            if state.strategy_retry_count < self.strategy_retry_budget:
                state.strategy_retry_count += 1
                decision = RecoveryDecision(
                    action="strategy_retry",
                    failure_category="no_visible_change",
                    reason="action retry budget exhausted, switching strategy",
                )
                state.last_recovery = decision
                return decision
            decision = RecoveryDecision(
                action="replan",
                failure_category="no_visible_change",
                reason="local recovery is exhausted for the current subgoal",
            )
            state.last_recovery = decision
            return decision

        decision = RecoveryDecision(action="replan", reason="no recovery rule matched")
        state.last_recovery = decision
        return decision
