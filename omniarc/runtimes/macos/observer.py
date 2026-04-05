from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from omniarc.core.models import Observation


def build_observation(
    *,
    screenshot_path: str,
    active_app: str,
    window_title: str | None = None,
    ui_tree: dict | None = None,
    ocr_blocks: list[dict] | None = None,
    platform_metadata: dict | None = None,
) -> Observation:
    return Observation(
        screenshot_path=screenshot_path,
        active_app=active_app,
        window_title=window_title,
        ui_tree=ui_tree,
        ocr_blocks=ocr_blocks or [],
        platform_metadata=platform_metadata or {},
    )


class MacOSObserver:
    def __init__(self, *, artifacts_dir: Path, dry_run: bool = False) -> None:
        self.artifacts_dir = artifacts_dir
        self.dry_run = dry_run

    async def observe(self) -> Observation:
        screenshot_path = self._capture_screenshot()
        active_app = self._get_active_app()
        window_title = self._get_window_title()
        return build_observation(
            screenshot_path=str(screenshot_path),
            active_app=active_app,
            window_title=window_title,
            platform_metadata=self._platform_metadata_for_screenshot(screenshot_path),
        )

    def _platform_metadata_for_screenshot(self, screenshot_path: Path) -> dict:
        try:
            digest = hashlib.sha256(screenshot_path.read_bytes()).hexdigest()
        except OSError:
            return {}
        return {"screenshot_sha256": digest}

    def _capture_screenshot(self) -> Path:
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        target = self.artifacts_dir / "latest.png"
        if self.dry_run:
            target.write_bytes(b"")
            return target
        subprocess.run(["screencapture", "-x", str(target)], check=False)
        return target

    def _run_osascript(self, script: str) -> str:
        completed = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            return ""
        return completed.stdout.strip()

    def _get_active_app(self) -> str:
        if self.dry_run:
            return "DryRunApp"
        return (
            self._run_osascript(
                'tell application "System Events" to get name of first application process whose frontmost is true'
            )
            or "UnknownApp"
        )

    def _get_window_title(self) -> str | None:
        if self.dry_run:
            return "DryRunWindow"
        title = self._run_osascript(
            'tell application "System Events" to tell process (name of first application process whose frontmost is true) to get name of front window'
        )
        return title or None
