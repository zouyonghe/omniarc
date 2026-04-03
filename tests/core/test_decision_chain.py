import pytest

from omniarc.core.agent import OmniArcAgent
from omniarc.core.models import ActionResult, Observation, TaskSpec


class FakeObserver:
    async def observe(self) -> Observation:
        return Observation(screenshot_path="step.png", active_app="Finder")


class FakeExecutor:
    def __init__(self) -> None:
        self.actions = []

    async def execute(self, actions):
        self.actions.extend(actions)
        if actions[0].kind == "done":
            return [ActionResult(success=True, is_done=True)]
        return [ActionResult(success=True)]


@pytest.mark.asyncio
async def test_agent_emits_non_terminal_actions_before_done() -> None:
    executor = FakeExecutor()
    agent = OmniArcAgent.build_for_test(
        observer=FakeObserver(),
        executor=executor,
        task=TaskSpec(task="Open Finder"),
    )

    status = await agent.run(max_steps=3)

    assert [action.kind for action in executor.actions[:2]] == ["open_app", "wait"]
    assert executor.actions[-1].kind == "done"
    assert status.status == "completed"
