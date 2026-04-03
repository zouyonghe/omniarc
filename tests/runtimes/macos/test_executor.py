import pytest

from omniarc.core.models import Action, ActionResult
from omniarc.runtimes.macos.executor import (
    MacOSExecutor,
    scroll_amounts_from_params,
    scroll_delta_from_amount,
    to_pixel_point,
)


@pytest.mark.asyncio
async def test_executor_rejects_unsupported_action_kind() -> None:
    executor = MacOSExecutor(dry_run=True)
    results = await executor.execute([Action(kind="run_powershell", params={})])
    assert results[0].success is False
    assert results[0].error_type == "runtime_error"


@pytest.mark.asyncio
async def test_executor_dry_run_click_succeeds() -> None:
    executor = MacOSExecutor(dry_run=True)
    results = await executor.execute([Action(kind="click", params={"x": 10, "y": 20})])
    assert results[0].success is True
    assert results[0].extracted_content == "dry-run click"


@pytest.mark.asyncio
async def test_executor_routes_real_click_to_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executor = MacOSExecutor(dry_run=False)

    async def fake_backend(action: Action) -> ActionResult:
        return ActionResult(extracted_content=f"backend {action.kind}")

    monkeypatch.setattr(executor, "_run_pointer_action", fake_backend)
    results = await executor.execute([Action(kind="click", params={"x": 1, "y": 2})])
    assert results[0].extracted_content == "backend click"


@pytest.mark.asyncio
async def test_executor_routes_real_type_text_to_paste_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executor = MacOSExecutor(dry_run=False)
    captured = []

    def fake_paste_text(text: str) -> None:
        captured.append(text)

    monkeypatch.setattr(executor, "_paste_text", fake_paste_text, raising=False)

    results = await executor.execute(
        [Action(kind="type_text", params={"text": "https://openai.com"})]
    )

    assert captured == ["https://openai.com"]
    assert results[0].success is True


def test_paste_text_uses_clipboard_and_restores_previous_contents(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    executor = MacOSExecutor(dry_run=False)
    calls = []

    class Result:
        def __init__(self, stdout=b"", returncode=0) -> None:
            self.stdout = stdout
            self.returncode = returncode

    def fake_run(command, **kwargs):
        calls.append((command, kwargs.get("input")))
        if command == ["pbpaste"]:
            return Result(stdout=b"original clipboard")
        return Result()

    def fake_hotkey(key: str, modifiers: list[str]) -> None:
        calls.append((["hotkey", key, *modifiers], None))

    monkeypatch.setattr("omniarc.runtimes.macos.executor.subprocess.run", fake_run)
    monkeypatch.setattr(executor, "_hotkey", fake_hotkey)

    executor._paste_text("OmniArc MCP")

    assert calls == [
        (["pbpaste"], None),
        (["pbcopy"], b"OmniArc MCP"),
        (["hotkey", "v", "cmd"], None),
        (["pbcopy"], b"original clipboard"),
    ]


def test_to_pixel_point_supports_0_to_1000_coordinates() -> None:
    assert to_pixel_point({"x": 500, "y": 250}, 200, 400) == (100, 100)


def test_scroll_delta_from_amount_keeps_sign_direction() -> None:
    assert scroll_delta_from_amount(3) == 3
    assert scroll_delta_from_amount(-2) == -2


def test_scroll_amounts_from_params_supports_direction_and_repeat() -> None:
    assert scroll_amounts_from_params(
        {"direction": "up", "amount": 2, "repeat": 3}
    ) == [
        2,
        2,
        2,
    ]
    assert scroll_amounts_from_params(
        {"direction": "down", "amount": 2, "repeat": 2}
    ) == [-2, -2]


def test_scroll_applies_modifier_flags_and_posts_repeated_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = []
    posted = []

    class FakeQuartz:
        kCGScrollEventUnitLine = 1
        kCGHIDEventTap = 2
        kCGEventFlagMaskCommand = 10

        def CGEventCreateScrollWheelEvent(self, _source, _unit, _wheels, amount):
            event = {"amount": amount}
            created.append(event)
            return event

        def CGEventSetFlags(self, event, flags):
            event["flags"] = flags

        def CGEventPost(self, _tap, event):
            posted.append(event.copy())

    monkeypatch.setattr(
        "omniarc.runtimes.macos.executor._load_quartz", lambda: FakeQuartz()
    )

    executor = MacOSExecutor(dry_run=False)
    executor._scroll(
        {"direction": "up", "amount": 1, "repeat": 2, "modifiers": ["cmd"]}
    )

    assert created == [
        {"amount": 1, "flags": 10},
        {"amount": 1, "flags": 10},
    ]
    assert posted == [
        {"amount": 1, "flags": 10},
        {"amount": 1, "flags": 10},
    ]
