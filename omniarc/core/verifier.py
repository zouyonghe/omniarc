from __future__ import annotations

import re

from omniarc.core.models import Action, Observation, VerificationResult


class StepVerifier:
    PROGRESS_ACTIONS = {
        "click",
        "double_click",
        "type_text",
        "press_key",
        "hotkey",
        "scroll",
        "drag",
    }

    def _expected_app(self, actions: list[Action]) -> str | None:
        for action in actions:
            if action.kind == "open_app":
                return str(action.params.get("name"))
        return None

    def _expected_app_from_task(self, task_text: str) -> str | None:
        lowered = task_text.lower().strip()
        if lowered.startswith("open safari") or lowered.startswith("go to "):
            return "Safari"
        if lowered.startswith("open finder"):
            return "Finder"
        if lowered.startswith("open notes"):
            return "Notes"
        if lowered.startswith("open terminal"):
            return "Terminal"
        if lowered.startswith("open notepad"):
            return "Notepad"
        return None

    def _requires_browser_content_evidence(self, task_text: str) -> bool:
        lowered = task_text.lower()
        return ("safari" in lowered or lowered.startswith("go to ")) and (
            "go to " in lowered
            or "search" in lowered
            or "zoom" in lowered
            or "scroll" in lowered
        )

    def _matched_text(self, task_text: str, observation: Observation) -> str | None:
        lowered_task = task_text.lower()
        expected_texts = [
            "Example Domain" if "example.com" in lowered_task else None,
        ]
        for block in observation.ocr_blocks:
            text = str(block.get("text", ""))
            if text and text in expected_texts:
                return text
        return None

    def _matched_window_title(
        self, task_text: str, observation: Observation
    ) -> str | None:
        if not self._requires_browser_content_evidence(task_text):
            return None
        title = observation.window_title
        if not title or title == "DryRunWindow":
            return None
        lowered_task = task_text.lower()
        if "search for " in lowered_task:
            query = lowered_task.split("search for ", 1)[1].strip()
            if query and query in title.lower():
                return title
            return None
        if "go to " in lowered_task:
            destination = lowered_task.split("go to ", 1)[1]
            for suffix in (
                " and zoom in",
                " and zoom out",
                " and scroll down",
                " and scroll up",
                " and search for ",
            ):
                if suffix in destination:
                    destination = destination.split(suffix, 1)[0]
            tokens = [
                token
                for token in re.split(r"[^a-z0-9]+", destination)
                if len(token) >= 4
                and token
                not in {"https", "http", "www", "com", "org", "wiki", "maps", "place"}
            ]
            if tokens and any(token in title.lower() for token in tokens):
                return title
            return None
        return title

    def _same_screenshot_content(self, before: Observation, after: Observation) -> bool:
        before_hash = before.platform_metadata.get("screenshot_sha256")
        after_hash = after.platform_metadata.get("screenshot_sha256")
        if before_hash and after_hash:
            return str(before_hash) == str(after_hash)
        return before.screenshot_path == after.screenshot_path

    def verify(
        self,
        *,
        task_text: str,
        actions: list[Action],
        before: Observation | None,
        after: Observation,
    ) -> VerificationResult:
        if after.active_app.startswith("DryRun"):
            if any(action.kind == "done" for action in actions):
                return VerificationResult(
                    status="complete",
                    evidence={"mode": "dry_run", "actual_app": after.active_app},
                )
            return VerificationResult(
                status="step_complete",
                evidence={"mode": "dry_run", "actual_app": after.active_app},
            )

        expected_app = self._expected_app(actions) or self._expected_app_from_task(
            task_text
        )
        if expected_app and after.active_app != expected_app:
            return VerificationResult(
                status="wrong_app",
                failure_category="wrong_app",
                evidence={"expected_app": expected_app, "actual_app": after.active_app},
            )

        if before is not None:
            unchanged = (
                self._same_screenshot_content(before, after)
                and before.active_app == after.active_app
                and before.window_title == after.window_title
                and before.ocr_blocks == after.ocr_blocks
            )
            if unchanged and any(
                action.kind in self.PROGRESS_ACTIONS for action in actions
            ):
                return VerificationResult(
                    status="no_visible_change",
                    failure_category="no_visible_change",
                    evidence={"reason": "observation did not change"},
                )

        matched_text = self._matched_text(task_text, after)
        matched_window_title = self._matched_window_title(task_text, after)
        matched_app = expected_app is not None and after.active_app == expected_app
        has_browser_evidence = matched_text or matched_window_title
        if any(action.kind == "done" for action in actions) and has_browser_evidence:
            return VerificationResult(
                status="complete",
                evidence={
                    **({"matched_text": matched_text} if matched_text else {}),
                    **(
                        {"matched_window_title": matched_window_title}
                        if matched_window_title
                        else {}
                    ),
                    **({"matched_app": after.active_app} if matched_app else {}),
                },
            )
        if (
            any(action.kind == "done" for action in actions)
            and matched_app
            and not self._requires_browser_content_evidence(task_text)
        ):
            return VerificationResult(
                status="complete",
                evidence={"matched_app": after.active_app},
            )
        if any(action.kind == "done" for action in actions):
            return VerificationResult(
                status="progress",
                evidence={
                    **({"matched_text": matched_text} if matched_text else {}),
                    **(
                        {"matched_window_title": matched_window_title}
                        if matched_window_title
                        else {}
                    ),
                    **({"matched_app": after.active_app} if matched_app else {}),
                },
            )
        if any(action.kind == "wait" for action in actions):
            return VerificationResult(
                status="step_complete",
                evidence={
                    **({"matched_text": matched_text} if matched_text else {}),
                    **(
                        {"matched_window_title": matched_window_title}
                        if matched_window_title
                        else {}
                    ),
                    **({"matched_app": after.active_app} if matched_app else {}),
                },
            )
        if has_browser_evidence or matched_app:
            return VerificationResult(
                status="step_complete",
                evidence={
                    **({"matched_text": matched_text} if matched_text else {}),
                    **(
                        {"matched_window_title": matched_window_title}
                        if matched_window_title
                        else {}
                    ),
                    **({"matched_app": after.active_app} if matched_app else {}),
                },
            )
        return VerificationResult(status="progress", evidence={})
