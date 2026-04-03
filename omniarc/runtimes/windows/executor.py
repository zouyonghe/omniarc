from __future__ import annotations

import asyncio
import subprocess

from omniarc.core.models import Action, ActionResult


class WindowsExecutor:
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
                error_message=f"Unsupported action kind for Windows runtime: {action.kind}",
            )
        return await handler(action)

    async def _handle_click(self, action: Action) -> ActionResult:
        return await self._dry_or_placeholder(action)

    async def _handle_double_click(self, action: Action) -> ActionResult:
        return await self._dry_or_placeholder(action)

    async def _handle_drag(self, action: Action) -> ActionResult:
        return await self._dry_or_placeholder(action)

    async def _handle_scroll(self, action: Action) -> ActionResult:
        return await self._dry_or_placeholder(action)

    async def _handle_type_text(self, action: Action) -> ActionResult:
        return await self._dry_or_placeholder(action)

    async def _handle_press_key(self, action: Action) -> ActionResult:
        return await self._dry_or_placeholder(action)

    async def _handle_hotkey(self, action: Action) -> ActionResult:
        return await self._dry_or_placeholder(action)

    async def _handle_wait(self, action: Action) -> ActionResult:
        duration = float(action.params.get("seconds", 1))
        if not self.dry_run:
            await asyncio.sleep(duration)
        return ActionResult(extracted_content=f"waited {duration} seconds")

    async def _handle_done(self, action: Action) -> ActionResult:
        return ActionResult(extracted_content="done", is_done=True)

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
            ["powershell", "-NoProfile", "-Command", f'Start-Process "{app_name}"'],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return ActionResult(
                success=False,
                error_type="runtime_error",
                error_message=completed.stderr.strip()
                or f"failed to open app {app_name}",
            )
        return ActionResult(extracted_content=f"opened app: {app_name}")

    async def _handle_run_powershell(self, action: Action) -> ActionResult:
        script = str(action.params.get("script", "")).strip()
        if self.dry_run:
            return ActionResult(extracted_content=f"dry-run powershell: {script}")
        if not script:
            return ActionResult(
                success=False,
                error_type="runtime_error",
                error_message="missing PowerShell source",
            )
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return ActionResult(
                success=False,
                error_type="runtime_error",
                error_message=completed.stderr.strip() or "PowerShell failed",
            )
        return ActionResult(extracted_content=completed.stdout.strip())

    async def _handle_run_applescript(self, action: Action) -> ActionResult:
        return ActionResult(
            success=False,
            error_type="runtime_error",
            error_message="run_applescript is not supported on Windows",
        )

    async def _dry_or_placeholder(self, action: Action) -> ActionResult:
        if self.dry_run:
            return ActionResult(extracted_content=f"dry-run {action.kind}")
        return ActionResult(
            success=False,
            error_type="runtime_error",
            error_message=f"{action.kind} requires a real Windows automation backend",
        )
