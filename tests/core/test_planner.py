import pytest

from omniarc.core.models import TaskSpec
from omniarc.core.planner import Planner


def _expected_zoom_steps(key: str) -> list[dict]:
    steps: list[dict] = []
    for _ in range(3):
        steps.extend(
            [
                {"kind": "hotkey", "params": {"key": key, "modifiers": ["cmd"]}},
                {"kind": "wait", "params": {"seconds": 0.5}},
            ]
        )
    return steps


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


@pytest.mark.asyncio
async def test_planner_builds_notepad_launch_steps() -> None:
    planner = Planner()

    plan = await planner.plan(TaskSpec(task="Open Notepad", runtime="windows"))

    assert [step["kind"] for step in plan["steps"]] == [
        "open_app",
        "wait",
        "done",
    ]
    assert plan["steps"][0]["params"]["name"] == "Notepad"


@pytest.mark.asyncio
async def test_planner_rejects_notepad_without_windows_runtime() -> None:
    planner = Planner()

    plan = await planner.plan(TaskSpec(task="Open Notepad"))

    assert plan["status"] == "unsupported_task"
    assert plan["steps"] == []


@pytest.mark.asyncio
async def test_planner_rejects_notepad_outside_windows_runtime() -> None:
    planner = Planner()

    plan = await planner.plan(TaskSpec(task="Open Notepad", runtime="macos"))

    assert plan["status"] == "unsupported_task"
    assert plan["steps"] == []


@pytest.mark.asyncio
async def test_planner_builds_navigation_then_page_zoom_in_steps() -> None:
    planner = Planner()

    plan = await planner.plan(
        TaskSpec(task="Open Safari and go to example.com and zoom in")
    )

    assert [step["kind"] for step in plan["steps"]] == [
        "open_app",
        "wait",
        "hotkey",
        "type_text",
        "press_key",
        "wait",
        "hotkey",
        "wait",
        "hotkey",
        "wait",
        "hotkey",
        "wait",
        "done",
    ]
    assert plan["steps"][3]["params"]["text"] == "https://example.com"
    assert plan["steps"][6:12] == _expected_zoom_steps("=")


@pytest.mark.asyncio
async def test_planner_builds_generic_navigation_then_page_zoom_in_steps() -> None:
    planner = Planner()

    plan = await planner.plan(
        TaskSpec(task="Open Safari and go to openai.com and zoom in")
    )

    assert [step["kind"] for step in plan["steps"]] == [
        "open_app",
        "wait",
        "hotkey",
        "type_text",
        "press_key",
        "wait",
        "hotkey",
        "wait",
        "hotkey",
        "wait",
        "hotkey",
        "wait",
        "done",
    ]
    assert plan["steps"][3]["params"]["text"] == "https://openai.com"
    assert plan["steps"][6:12] == _expected_zoom_steps("=")


@pytest.mark.asyncio
async def test_planner_builds_bare_navigation_then_page_zoom_in_steps() -> None:
    planner = Planner()

    plan = await planner.plan(TaskSpec(task="Go to openai.com and zoom in"))

    assert [step["kind"] for step in plan["steps"]] == [
        "open_app",
        "wait",
        "hotkey",
        "type_text",
        "press_key",
        "wait",
        "hotkey",
        "wait",
        "hotkey",
        "wait",
        "hotkey",
        "wait",
        "done",
    ]
    assert plan["steps"][3]["params"]["text"] == "https://openai.com"
    assert plan["steps"][6:12] == _expected_zoom_steps("=")


@pytest.mark.asyncio
async def test_planner_builds_page_zoom_out_without_navigation() -> None:
    planner = Planner()

    plan = await planner.plan(TaskSpec(task="Open Safari and zoom out"))

    assert [step["kind"] for step in plan["steps"]] == [
        "open_app",
        "wait",
        "hotkey",
        "wait",
        "hotkey",
        "wait",
        "hotkey",
        "wait",
        "done",
    ]
    assert plan["steps"][2:8] == _expected_zoom_steps("-")


@pytest.mark.asyncio
async def test_planner_builds_page_zoom_in_without_navigation() -> None:
    planner = Planner()

    plan = await planner.plan(TaskSpec(task="Open Safari and zoom in"))

    assert [step["kind"] for step in plan["steps"]] == [
        "open_app",
        "wait",
        "hotkey",
        "wait",
        "hotkey",
        "wait",
        "hotkey",
        "wait",
        "done",
    ]
    assert plan["steps"][2:8] == _expected_zoom_steps("=")


@pytest.mark.asyncio
async def test_planner_builds_generic_navigation_then_page_zoom_out_steps() -> None:
    planner = Planner()

    plan = await planner.plan(
        TaskSpec(task="Open Safari and go to openai.com and zoom out")
    )

    assert [step["kind"] for step in plan["steps"]] == [
        "open_app",
        "wait",
        "hotkey",
        "type_text",
        "press_key",
        "wait",
        "hotkey",
        "wait",
        "hotkey",
        "wait",
        "hotkey",
        "wait",
        "done",
    ]
    assert plan["steps"][3]["params"]["text"] == "https://openai.com"
    assert plan["steps"][6:12] == _expected_zoom_steps("-")


@pytest.mark.asyncio
async def test_planner_builds_bare_navigation_then_page_zoom_out_steps() -> None:
    planner = Planner()

    plan = await planner.plan(TaskSpec(task="Go to openai.com and zoom out"))

    assert [step["kind"] for step in plan["steps"]] == [
        "open_app",
        "wait",
        "hotkey",
        "type_text",
        "press_key",
        "wait",
        "hotkey",
        "wait",
        "hotkey",
        "wait",
        "hotkey",
        "wait",
        "done",
    ]
    assert plan["steps"][3]["params"]["text"] == "https://openai.com"
    assert plan["steps"][6:12] == _expected_zoom_steps("-")


@pytest.mark.asyncio
async def test_planner_builds_google_maps_zoom_steps() -> None:
    planner = Planner()

    plan = await planner.plan(
        TaskSpec(
            task="Open Safari and go to google.com/maps/place/Washington and zoom in"
        )
    )

    assert [step["kind"] for step in plan["steps"]] == [
        "open_app",
        "wait",
        "hotkey",
        "type_text",
        "press_key",
        "wait",
        "click",
        "scroll",
        "wait",
        "done",
    ]
    assert (
        plan["steps"][3]["params"]["text"] == "https://google.com/maps/place/Washington"
    )
    assert plan["steps"][6] == {"kind": "click", "params": {"x": 800, "y": 500}}
    assert plan["steps"][7] == {
        "kind": "scroll",
        "params": {"direction": "up", "amount": 1, "repeat": 16},
    }


@pytest.mark.asyncio
async def test_planner_builds_navigation_then_page_scroll_down_steps() -> None:
    planner = Planner()

    plan = await planner.plan(
        TaskSpec(
            task="Open Safari and go to en.wikipedia.org/wiki/Washington,_D.C. and scroll down"
        )
    )

    assert [step["kind"] for step in plan["steps"]] == [
        "open_app",
        "wait",
        "hotkey",
        "type_text",
        "press_key",
        "wait",
        "scroll",
        "wait",
        "done",
    ]
    assert (
        plan["steps"][3]["params"]["text"]
        == "https://en.wikipedia.org/wiki/Washington,_D.C."
    )
    assert plan["steps"][6] == {
        "kind": "scroll",
        "params": {"direction": "down", "amount": 5, "repeat": 8},
    }


@pytest.mark.asyncio
async def test_planner_rejects_chained_browser_phrase_in_zoom_variant() -> None:
    planner = Planner()

    plan = await planner.plan(
        TaskSpec(
            task="Open Safari and go to example.com and click subscribe and zoom in"
        )
    )

    assert plan["status"] == "unsupported_task"
    assert plan["steps"] == []


@pytest.mark.asyncio
async def test_planner_builds_bare_navigation_then_page_scroll_up_steps() -> None:
    planner = Planner()

    plan = await planner.plan(
        TaskSpec(task="Go to en.wikipedia.org/wiki/Washington,_D.C. and scroll up")
    )

    assert [step["kind"] for step in plan["steps"]] == [
        "open_app",
        "wait",
        "hotkey",
        "type_text",
        "press_key",
        "wait",
        "scroll",
        "wait",
        "done",
    ]
    assert (
        plan["steps"][3]["params"]["text"]
        == "https://en.wikipedia.org/wiki/Washington,_D.C."
    )
    assert plan["steps"][6] == {
        "kind": "scroll",
        "params": {"direction": "up", "amount": 5, "repeat": 8},
    }
