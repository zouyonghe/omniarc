from pathlib import Path

import pytest

from omniarc.runtimes.macos.observer import MacOSObserver, build_observation


def test_build_observation_keeps_active_app_and_window_title() -> None:
    observation = build_observation(
        screenshot_path="step-0001.png",
        active_app="Safari",
        window_title="Example Domain",
    )
    assert observation.active_app == "Safari"
    assert observation.window_title == "Example Domain"


@pytest.mark.asyncio
async def test_observer_records_screenshot_hash_in_platform_metadata(
    tmp_path: Path,
) -> None:
    screenshot_path = tmp_path / "latest.png"
    screenshot_path.write_bytes(b"fake-image")

    observer = MacOSObserver(artifacts_dir=tmp_path, dry_run=False)
    observer._capture_screenshot = lambda: screenshot_path
    observer._get_active_app = lambda: "Safari"
    observer._get_window_title = lambda: "Example Domain"

    observation = await observer.observe()

    assert observation.platform_metadata["screenshot_sha256"]
