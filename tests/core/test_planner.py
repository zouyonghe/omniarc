import pytest

from omniarc.core.models import TaskSpec
from omniarc.core.planner import Planner


@pytest.mark.asyncio
async def test_planner_builds_safari_navigation_steps() -> None:
    planner = Planner()

    plan = await planner.plan(TaskSpec(task="Open Safari and go to example.com"))

    assert [step["kind"] for step in plan["steps"]] == [
        "open_app",
        "wait",
        "hotkey",
        "type_text",
        "press_key",
        "wait",
        "done",
    ]
    assert plan["steps"][0]["params"]["name"] == "Safari"
    assert plan["steps"][3]["params"]["text"] == "https://example.com"


@pytest.mark.asyncio
async def test_planner_builds_safari_search_steps() -> None:
    planner = Planner()

    plan = await planner.plan(TaskSpec(task="Open Safari and search for OmniArc MCP"))

    assert plan["steps"][0]["kind"] == "open_app"
    assert plan["steps"][0]["params"]["name"] == "Safari"
    assert plan["steps"][3]["kind"] == "type_text"
    assert plan["steps"][3]["params"]["text"] == "OmniArc MCP"
    assert plan["steps"][-1]["kind"] == "done"


@pytest.mark.asyncio
async def test_planner_builds_common_app_launch_steps() -> None:
    planner = Planner()

    plan = await planner.plan(TaskSpec(task="Open Finder"))

    assert [step["kind"] for step in plan["steps"]] == [
        "open_app",
        "wait",
        "done",
    ]
    assert plan["steps"][0]["params"]["name"] == "Finder"
