from __future__ import annotations

import asyncio
import json
import subprocess
import time
from typing import Any

from omniarc.core.models import Action, ActionResult

SPECIAL_KEY_CODES = {
    "enter": 36,
    "return": 36,
    "tab": 48,
    "space": 49,
    "delete": 51,
    "backspace": 51,
    "escape": 53,
    "esc": 53,
    "left": 123,
    "right": 124,
    "down": 125,
    "up": 126,
}

MODIFIER_NAMES = {
    "cmd": "command",
    "command": "command",
    "ctrl": "control",
    "control": "control",
    "opt": "option",
    "option": "option",
    "alt": "option",
    "shift": "shift",
}

MODIFIER_EVENT_FLAGS = {
    "command": "kCGEventFlagMaskCommand",
    "control": "kCGEventFlagMaskControl",
    "option": "kCGEventFlagMaskAlternate",
    "shift": "kCGEventFlagMaskShift",
}


def to_pixel_point(
    position: dict[str, Any], screen_width: int, screen_height: int
) -> tuple[int, int]:
    x = float(position.get("x", 0))
    y = float(position.get("y", 0))
    if x > 1 or y > 1:
        return (
            int(round(x / 1000 * screen_width)),
            int(round(y / 1000 * screen_height)),
        )
    return (int(round(x * screen_width)), int(round(y * screen_height)))


def scroll_delta_from_amount(amount: int | float) -> int:
    return int(amount)


def scroll_amounts_from_params(params: dict[str, Any]) -> list[int]:
    amount = scroll_delta_from_amount(params.get("amount", 1))
    direction = str(params.get("direction", "")).strip().lower()
    if direction == "up":
        amount = abs(amount)
    elif direction == "down":
        amount = -abs(amount)
    repeat = max(1, int(params.get("repeat", 1)))
    return [amount] * repeat


def _load_quartz():
    try:
        import Quartz  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Quartz backend is unavailable; install pyobjc-framework-Quartz"
        ) from exc
    return Quartz


def _screen_size() -> tuple[int, int]:
    quartz = _load_quartz()
    display_id = quartz.CGMainDisplayID()
    return quartz.CGDisplayPixelsWide(display_id), quartz.CGDisplayPixelsHigh(
        display_id
    )


def _modifier_tokens(modifiers: list[str] | tuple[str, ...]) -> list[str]:
    tokens: list[str] = []
    for name in modifiers:
        normalized = MODIFIER_NAMES.get(str(name).lower())
        if normalized and normalized not in tokens:
            tokens.append(normalized)
    return tokens


def quartz_modifier_flags(quartz: Any, modifiers: list[str] | tuple[str, ...]) -> int:
    flags = 0
    for token in _modifier_tokens(modifiers):
        flag_name = MODIFIER_EVENT_FLAGS.get(token)
        if flag_name is None:
            continue
        flags |= int(getattr(quartz, flag_name, 0))
    return flags


def _escape_applescript_string(text: str) -> str:
    return json.dumps(text, ensure_ascii=False)


class MacOSExecutor:
    def __init__(self, *, dry_run: bool = False) -> None:
        self.dry_run = dry_run

    async def execute(self, actions: list[Action]) -> list[ActionResult]:
        results: list[ActionResult] = []
        for action in actions:
            results.append(await self._execute_one(action))
        return results

    async def _execute_one(self, action: Action) -> ActionResult:
        handler = getattr(self, f"_handle_{action.kind}", None)
        if handler is None:
            return ActionResult(
                success=False,
                error_type="runtime_error",
                error_message=f"Unsupported action kind for macOS runtime: {action.kind}",
            )
        return await handler(action)

    async def _handle_click(self, action: Action) -> ActionResult:
        return await self._run_pointer_action(action)

    async def _handle_double_click(self, action: Action) -> ActionResult:
        return await self._run_pointer_action(action)

    async def _handle_drag(self, action: Action) -> ActionResult:
        return await self._run_pointer_action(action)

    async def _handle_scroll(self, action: Action) -> ActionResult:
        return await self._run_pointer_action(action)

    async def _handle_type_text(self, action: Action) -> ActionResult:
        return await self._run_keyboard_action(action)

    async def _handle_press_key(self, action: Action) -> ActionResult:
        return await self._run_keyboard_action(action)

    async def _handle_hotkey(self, action: Action) -> ActionResult:
        return await self._run_keyboard_action(action)

    async def _handle_run_applescript(self, action: Action) -> ActionResult:
        script = str(action.params.get("script", "")).strip()
        if self.dry_run:
            return ActionResult(extracted_content=f"dry-run applescript: {script}")
        if not script:
            return ActionResult(
                success=False,
                error_type="runtime_error",
                error_message="missing AppleScript source",
            )
        try:
            self._run_applescript_text(script)
        except Exception as exc:
            return ActionResult(
                success=False,
                error_type="runtime_error",
                error_message=str(exc),
            )
        return ActionResult(extracted_content="executed applescript")

    async def _handle_open_app(self, action: Action) -> ActionResult:
        app_name = str(action.params.get("name", "")).strip()
        if not app_name:
            return ActionResult(
                success=False,
                error_type="runtime_error",
                error_message="missing app name",
            )
        if self.dry_run:
            return ActionResult(extracted_content=f"dry-run open app: {app_name}")
        completed = subprocess.run(
            ["open", "-a", app_name], capture_output=True, text=True, check=False
        )
        if completed.returncode != 0:
            return ActionResult(
                success=False,
                error_type="runtime_error",
                error_message=completed.stderr.strip()
                or f"failed to open app {app_name}",
            )
        return ActionResult(extracted_content=f"opened app: {app_name}")

    async def _handle_wait(self, action: Action) -> ActionResult:
        duration = float(action.params.get("seconds", 1))
        if not self.dry_run:
            await asyncio.sleep(duration)
        return ActionResult(extracted_content=f"waited {duration} seconds")

    async def _handle_done(self, action: Action) -> ActionResult:
        return ActionResult(extracted_content="done", is_done=True)

    async def _run_pointer_action(self, action: Action) -> ActionResult:
        if self.dry_run:
            return ActionResult(extracted_content=f"dry-run {action.kind}")
        try:
            if action.kind == "click":
                self._click(action.params, click_count=1)
            elif action.kind == "double_click":
                self._click(action.params, click_count=2)
            elif action.kind == "drag":
                self._drag(action.params)
            elif action.kind == "scroll":
                self._scroll(action.params)
            else:
                return ActionResult(
                    success=False,
                    error_type="runtime_error",
                    error_message=f"unsupported pointer action: {action.kind}",
                )
        except Exception as exc:
            return ActionResult(
                success=False,
                error_type="runtime_error",
                error_message=str(exc),
            )
        return ActionResult(extracted_content=f"executed {action.kind}")

    async def _run_keyboard_action(self, action: Action) -> ActionResult:
        if self.dry_run:
            return ActionResult(extracted_content=f"dry-run {action.kind}")
        try:
            if action.kind == "type_text":
                text = str(action.params.get("text", ""))
                if not text:
                    raise ValueError("missing text")
                self._paste_text(text)
            elif action.kind == "press_key":
                self._press_key(str(action.params.get("key", "")))
            elif action.kind == "hotkey":
                key = str(action.params.get("key", ""))
                modifiers = action.params.get("modifiers", [])
                if not isinstance(modifiers, list):
                    raise ValueError("modifiers must be a list")
                self._hotkey(key, modifiers)
            else:
                return ActionResult(
                    success=False,
                    error_type="runtime_error",
                    error_message=f"unsupported keyboard action: {action.kind}",
                )
        except Exception as exc:
            return ActionResult(
                success=False,
                error_type="runtime_error",
                error_message=str(exc),
            )
        return ActionResult(extracted_content=f"executed {action.kind}")

    def _paste_text(self, text: str) -> None:
        previous_clipboard = subprocess.run(
            ["pbpaste"],
            capture_output=True,
            check=False,
        ).stdout
        try:
            subprocess.run(
                ["pbcopy"],
                input=text.encode("utf-8"),
                check=False,
            )
            self._hotkey("v", ["cmd"])
            # Give the receiving app a moment to consume the pasted text
            # before restoring the user's clipboard.
            time.sleep(0.05)
        finally:
            subprocess.run(
                ["pbcopy"],
                input=previous_clipboard,
                check=False,
            )

    def _run_applescript_text(self, script: str) -> None:
        completed = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "AppleScript failed")

    def _press_key(self, key: str) -> None:
        normalized = key.strip().lower()
        if not normalized:
            raise ValueError("missing key")
        key_code = SPECIAL_KEY_CODES.get(normalized)
        if key_code is not None:
            script = f'tell application "System Events" to key code {key_code}'
        else:
            script = f'tell application "System Events" to keystroke {_escape_applescript_string(key)}'
        self._run_applescript_text(script)

    def _hotkey(self, key: str, modifiers: list[str]) -> None:
        normalized = key.strip().lower()
        if not normalized:
            raise ValueError("missing key")
        modifier_tokens = _modifier_tokens(modifiers)
        if not modifier_tokens:
            self._press_key(key)
            return
        using_clause = ", ".join(f"{token} down" for token in modifier_tokens)
        key_code = SPECIAL_KEY_CODES.get(normalized)
        if key_code is not None:
            script = f'tell application "System Events" to key code {key_code} using {{{using_clause}}}'
        else:
            script = f'tell application "System Events" to keystroke {_escape_applescript_string(key)} using {{{using_clause}}}'
        self._run_applescript_text(script)

    def _click(self, position: dict[str, Any], *, click_count: int) -> None:
        quartz = _load_quartz()
        screen_width, screen_height = _screen_size()
        point = to_pixel_point(position, screen_width, screen_height)
        for click_index in range(click_count):
            down = quartz.CGEventCreateMouseEvent(
                None,
                quartz.kCGEventLeftMouseDown,
                point,
                quartz.kCGMouseButtonLeft,
            )
            up = quartz.CGEventCreateMouseEvent(
                None,
                quartz.kCGEventLeftMouseUp,
                point,
                quartz.kCGMouseButtonLeft,
            )
            quartz.CGEventSetIntegerValueField(
                down,
                quartz.kCGMouseEventClickState,
                click_index + 1,
            )
            quartz.CGEventSetIntegerValueField(
                up,
                quartz.kCGMouseEventClickState,
                click_index + 1,
            )
            quartz.CGEventPost(quartz.kCGHIDEventTap, down)
            quartz.CGEventPost(quartz.kCGHIDEventTap, up)

    def _drag(self, params: dict[str, Any]) -> None:
        quartz = _load_quartz()
        screen_width, screen_height = _screen_size()
        start = to_pixel_point(params.get("start", {}), screen_width, screen_height)
        end = to_pixel_point(params.get("end", {}), screen_width, screen_height)
        down = quartz.CGEventCreateMouseEvent(
            None,
            quartz.kCGEventLeftMouseDown,
            start,
            quartz.kCGMouseButtonLeft,
        )
        drag = quartz.CGEventCreateMouseEvent(
            None,
            quartz.kCGEventLeftMouseDragged,
            end,
            quartz.kCGMouseButtonLeft,
        )
        up = quartz.CGEventCreateMouseEvent(
            None,
            quartz.kCGEventLeftMouseUp,
            end,
            quartz.kCGMouseButtonLeft,
        )
        quartz.CGEventPost(quartz.kCGHIDEventTap, down)
        quartz.CGEventPost(quartz.kCGHIDEventTap, drag)
        quartz.CGEventPost(quartz.kCGHIDEventTap, up)

    def _scroll(self, params: dict[str, Any]) -> None:
        quartz = _load_quartz()
        modifiers = params.get("modifiers", [])
        if not isinstance(modifiers, list):
            raise ValueError("modifiers must be a list")
        flags = quartz_modifier_flags(quartz, modifiers)
        for amount in scroll_amounts_from_params(params):
            event = quartz.CGEventCreateScrollWheelEvent(
                None,
                quartz.kCGScrollEventUnitLine,
                1,
                amount,
            )
            if flags:
                quartz.CGEventSetFlags(event, flags)
            quartz.CGEventPost(quartz.kCGHIDEventTap, event)
