import pytest

from omniarc.core.models import (
    Action,
    Observation,
    PlanBundle,
    PlanStep,
    PreplanResult,
    SearchArtifact,
    TaskSpec,
)
from omniarc.core.state import RunState


def test_action_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError):
        Action(kind="explode", params={})


def test_observation_requires_screenshot_path() -> None:
    observation = Observation(screenshot_path="step-0001.png", active_app="Safari")
    assert observation.screenshot_path.endswith(".png")


def test_task_spec_defaults_to_no_search() -> None:
    task = TaskSpec(task="Open Safari")
    assert task.allow_search is False


def test_preplan_result_defaults_are_stable() -> None:
    result = PreplanResult()

    assert result.planning_mode == "direct"
    assert result.search_queries == []
    assert result.selected_skills == []
    assert result.success_signals == []
    assert result.risk_flags == []


def test_search_artifact_serializes_to_json_payload() -> None:
    artifact = SearchArtifact(
        query="omniarc safari scroll",
        summary="Found the scroll shortcut docs",
        source="search",
    )

    assert artifact.model_dump(mode="json") == {
        "query": "omniarc safari scroll",
        "summary": "Found the scroll shortcut docs",
        "source": "search",
    }


def test_plan_step_requires_non_empty_goal() -> None:
    with pytest.raises(ValueError):
        PlanStep(
            goal="", completion_hint="Safari is open", allowed_actions=["open_app"]
        )


def test_plan_bundle_serializes_nested_preplan_and_steps() -> None:
    bundle = PlanBundle(
        summary="Search and summarize",
        status="supported",
        source="planner",
        preplan=PreplanResult(planning_mode="search"),
        steps=[
            PlanStep(
                goal="Open browser",
                completion_hint="Browser is frontmost",
                allowed_actions=["open_app"],
            )
        ],
        completion_criteria=["Target page loaded"],
        replan_triggers=["stalled_subgoal"],
    )

    payload = bundle.model_dump(mode="json")

    assert payload["preplan"]["planning_mode"] == "search"
    assert payload["steps"][0]["goal"] == "Open browser"
    assert payload["completion_criteria"] == ["Target page loaded"]


def test_run_state_defaults_new_planning_fields() -> None:
    state = RunState()

    assert state.preplan_result is None
    assert state.plan_bundle is None
    assert state.search_artifacts == []
    assert state.replan_count == 0
