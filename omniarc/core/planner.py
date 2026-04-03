from __future__ import annotations

from typing import Any

from omniarc.core.models import TaskSpec

COMMON_APPS = {
    "finder": "Finder",
    "notes": "Notes",
    "terminal": "Terminal",
    "safari": "Safari",
}


class Planner:
    def _browser_entry_steps(self) -> list[dict[str, Any]]:
        return [
            {"kind": "open_app", "params": {"name": "Safari"}},
            {"kind": "wait", "params": {"seconds": 1}},
            {"kind": "hotkey", "params": {"key": "l", "modifiers": ["cmd"]}},
        ]

    def _app_launch_steps(self, app_name: str) -> list[dict[str, Any]]:
        return [
            {"kind": "open_app", "params": {"name": app_name}},
            {"kind": "wait", "params": {"seconds": 1}},
            {"kind": "done", "params": {}},
        ]

    async def plan(self, task: TaskSpec) -> dict[str, Any]:
        text = task.task.strip()
        lowered = text.lower()
        if lowered.startswith("open safari and go to "):
            destination = text[len("Open Safari and go to ") :].strip()
            if destination and "://" not in destination:
                destination = f"https://{destination}"
            return {
                "summary": task.task,
                "steps": self._browser_entry_steps()
                + [
                    {"kind": "type_text", "params": {"text": destination}},
                    {"kind": "press_key", "params": {"key": "enter"}},
                    {"kind": "wait", "params": {"seconds": 1}},
                    {"kind": "done", "params": {}},
                ],
            }
        if lowered.startswith("open safari and search for "):
            query = text[len("Open Safari and search for ") :].strip()
            return {
                "summary": task.task,
                "steps": self._browser_entry_steps()
                + [
                    {"kind": "type_text", "params": {"text": query}},
                    {"kind": "press_key", "params": {"key": "enter"}},
                    {"kind": "wait", "params": {"seconds": 1}},
                    {"kind": "done", "params": {}},
                ],
            }
        if lowered.startswith("open "):
            app_key = lowered[len("open ") :].strip()
            app_name = COMMON_APPS.get(app_key)
            if app_name:
                return {"summary": task.task, "steps": self._app_launch_steps(app_name)}
        return {
            "summary": task.task,
            "steps": [{"kind": "done", "params": {}}],
        }
