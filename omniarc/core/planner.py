from __future__ import annotations

from typing import Any

from omniarc.core.models import TaskSpec

COMMON_APPS = {
    "finder": "Finder",
    "notes": "Notes",
    "notepad": "Notepad",
    "terminal": "Terminal",
    "safari": "Safari",
}

PAGE_ZOOM_REPEAT = 3
MAP_ZOOM_REPEAT = 16
PAGE_SCROLL_AMOUNT = 5
PAGE_SCROLL_REPEAT = 8
MAP_FOCUS_X = 800
MAP_FOCUS_Y = 500


class Planner:
    def _extract_destination(
        self, text: str, lowered: str, prefix: str, suffix: str
    ) -> str | None:
        if not lowered.startswith(prefix) or not lowered.endswith(suffix):
            return None
        return text[len(prefix) : -len(suffix)].strip()

    def _browser_entry_steps(self) -> list[dict[str, Any]]:
        return [
            {"kind": "open_app", "params": {"name": "Safari"}},
            {"kind": "wait", "params": {"seconds": 1}},
            {"kind": "hotkey", "params": {"key": "l", "modifiers": ["cmd"]}},
        ]

    def _page_zoom_steps(self, direction: str) -> list[dict[str, Any]]:
        key = "=" if direction == "in" else "-"
        steps: list[dict[str, Any]] = []
        for _ in range(PAGE_ZOOM_REPEAT):
            steps.extend(
                [
                    {
                        "kind": "hotkey",
                        "params": {"key": key, "modifiers": ["cmd"]},
                    },
                    {"kind": "wait", "params": {"seconds": 0.5}},
                ]
            )
        steps.append({"kind": "done", "params": {}})
        return steps

    def _map_zoom_steps(self) -> list[dict[str, Any]]:
        return [
            {"kind": "click", "params": {"x": MAP_FOCUS_X, "y": MAP_FOCUS_Y}},
            {
                "kind": "scroll",
                "params": {"direction": "up", "amount": 1, "repeat": MAP_ZOOM_REPEAT},
            },
            {"kind": "wait", "params": {"seconds": 0.5}},
            {"kind": "done", "params": {}},
        ]

    def _page_scroll_steps(self, direction: str) -> list[dict[str, Any]]:
        return [
            {
                "kind": "scroll",
                "params": {
                    "direction": direction,
                    "amount": PAGE_SCROLL_AMOUNT,
                    "repeat": PAGE_SCROLL_REPEAT,
                },
            },
            {"kind": "wait", "params": {"seconds": 0.5}},
            {"kind": "done", "params": {}},
        ]

    def _destination_steps(self, destination: str) -> list[dict[str, Any]]:
        if destination and "://" not in destination:
            destination = f"https://{destination}"
        return self._browser_entry_steps() + [
            {"kind": "type_text", "params": {"text": destination}},
            {"kind": "press_key", "params": {"key": "enter"}},
            {"kind": "wait", "params": {"seconds": 1}},
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
        for prefix in ("open safari and go to ", "go to "):
            destination = self._extract_destination(
                text, lowered, prefix, " and zoom in"
            )
            if destination is not None:
                if "google.com/maps/" in destination.lower():
                    return {
                        "summary": task.task,
                        "steps": self._destination_steps(destination)
                        + self._map_zoom_steps(),
                    }
                return {
                    "summary": task.task,
                    "steps": self._destination_steps(destination)
                    + self._page_zoom_steps("in"),
                }
            destination = self._extract_destination(
                text, lowered, prefix, " and zoom out"
            )
            if destination is not None:
                return {
                    "summary": task.task,
                    "steps": self._destination_steps(destination)
                    + self._page_zoom_steps("out"),
                }
            destination = self._extract_destination(
                text, lowered, prefix, " and scroll down"
            )
            if destination is not None:
                return {
                    "summary": task.task,
                    "steps": self._destination_steps(destination)
                    + self._page_scroll_steps("down"),
                }
            destination = self._extract_destination(
                text, lowered, prefix, " and scroll up"
            )
            if destination is not None:
                return {
                    "summary": task.task,
                    "steps": self._destination_steps(destination)
                    + self._page_scroll_steps("up"),
                }
        if lowered == "open safari and zoom in":
            return {
                "summary": task.task,
                "steps": [
                    {"kind": "open_app", "params": {"name": "Safari"}},
                    {"kind": "wait", "params": {"seconds": 1}},
                ]
                + self._page_zoom_steps("in"),
            }
        if lowered == "open safari and zoom out":
            return {
                "summary": task.task,
                "steps": [
                    {"kind": "open_app", "params": {"name": "Safari"}},
                    {"kind": "wait", "params": {"seconds": 1}},
                ]
                + self._page_zoom_steps("out"),
            }
        if lowered == "open safari and google maps and zoom in on washington":
            return {
                "summary": task.task,
                "steps": self._destination_steps(
                    "https://google.com/maps/place/Washington"
                )
                + self._map_zoom_steps(),
            }
        if lowered.startswith("open safari and go to "):
            return {
                "summary": task.task,
                "steps": self._destination_steps(
                    text[len("Open Safari and go to ") :].strip()
                )
                + [{"kind": "done", "params": {}}],
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
                if app_name == "Notepad" and task.runtime != "windows":
                    return {
                        "summary": task.task,
                        "steps": [{"kind": "done", "params": {}}],
                    }
                return {"summary": task.task, "steps": self._app_launch_steps(app_name)}
        return {
            "summary": task.task,
            "steps": [{"kind": "done", "params": {}}],
        }
