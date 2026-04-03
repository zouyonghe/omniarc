import pytest

from omniarc.core.agent import OmniArcAgent
from omniarc.core.models import Observation, TaskSpec


class FakeObserver:
    async def observe(self) -> Observation:
        return Observation(screenshot_path="step-0001.png", active_app="Finder")


class FakeExecutor:
    async def execute(self, actions):
        return OmniArcAgent.default_test_results()


@pytest.mark.asyncio
async def test_agent_reaches_completed_state() -> None:
    agent = OmniArcAgent.build_for_test(
        observer=FakeObserver(),
        executor=FakeExecutor(),
        task=TaskSpec(task="Do one thing"),
    )
    status = await agent.run(max_steps=1)
    assert status.status == "completed"
