import pytest

from omniarc.core.models import Action
from omniarc.runtimes.windows import (
    WindowsCapabilityProvider,
    WindowsExecutor,
    build_windows_observation,
)


def test_windows_capability_provider_exposes_minimum_set() -> None:
    capabilities = WindowsCapabilityProvider().get_capabilities()
    assert capabilities.supports("screen_capture") is True
    assert capabilities.supports("open_application") is True
    assert capabilities.supports("powershell") is True


def test_build_windows_observation_keeps_titles() -> None:
    observation = build_windows_observation(
        screenshot_path="latest.png",
        active_app="Notepad",
        window_title="notes.txt",
    )
    assert observation.active_app == "Notepad"
    assert observation.window_title == "notes.txt"


@pytest.mark.asyncio
async def test_windows_executor_dry_run_click_succeeds() -> None:
    executor = WindowsExecutor(dry_run=True)
    results = await executor.execute([Action(kind="click", params={"x": 10, "y": 10})])
    assert results[0].success is True
    assert results[0].extracted_content == "dry-run click"


@pytest.mark.asyncio
async def test_windows_executor_rejects_platform_mismatch_action() -> None:
    executor = WindowsExecutor(dry_run=True)
    results = await executor.execute([Action(kind="run_applescript", params={})])
    assert results[0].success is False
    assert results[0].error_type == "runtime_error"
