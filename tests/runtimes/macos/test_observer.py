from omniarc.runtimes.macos.observer import build_observation


def test_build_observation_keeps_active_app_and_window_title() -> None:
    observation = build_observation(
        screenshot_path="step-0001.png",
        active_app="Safari",
        window_title="Example Domain",
    )
    assert observation.active_app == "Safari"
    assert observation.window_title == "Example Domain"
