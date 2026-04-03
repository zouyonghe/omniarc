import pytest

from omniarc.core.models import Action, Observation, TaskSpec


def test_action_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError):
        Action(kind="explode", params={})


def test_observation_requires_screenshot_path() -> None:
    observation = Observation(screenshot_path="step-0001.png", active_app="Safari")
    assert observation.screenshot_path.endswith(".png")


def test_task_spec_defaults_to_no_search() -> None:
    task = TaskSpec(task="Open Safari")
    assert task.allow_search is False
