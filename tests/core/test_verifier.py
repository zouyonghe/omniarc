from __future__ import annotations

from omniarc.core.models import Action, Observation, VerificationResult
from omniarc.core.verifier import StepVerifier


def _observation(
    *,
    screenshot_path: str,
    active_app: str,
    window_title: str | None = None,
    ocr_texts: list[str] | None = None,
) -> Observation:
    return Observation(
        screenshot_path=screenshot_path,
        active_app=active_app,
        window_title=window_title,
        ocr_blocks=[{"text": text} for text in (ocr_texts or [])],
    )


def test_verifier_flags_wrong_app_when_expected_app_is_not_frontmost() -> None:
    verifier = StepVerifier()
    result = verifier.verify(
        task_text="Open Safari and go to example.com",
        actions=[Action(kind="open_app", params={"name": "Safari"})],
        before=None,
        after=_observation(screenshot_path="after.png", active_app="Codex"),
    )

    assert result == VerificationResult(
        status="wrong_app",
        failure_category="wrong_app",
        evidence={"expected_app": "Safari", "actual_app": "Codex"},
    )


def test_verifier_flags_no_visible_change_when_observation_is_unchanged() -> None:
    verifier = StepVerifier()
    before = _observation(
        screenshot_path="same.png",
        active_app="Safari",
        window_title="Example Domain",
        ocr_texts=["Example Domain"],
    )
    after = _observation(
        screenshot_path="same.png",
        active_app="Safari",
        window_title="Example Domain",
        ocr_texts=["Example Domain"],
    )

    result = verifier.verify(
        task_text="Open Safari and go to example.com and scroll down",
        actions=[Action(kind="scroll", params={"direction": "down"})],
        before=before,
        after=after,
    )

    assert result == VerificationResult(
        status="no_visible_change",
        failure_category="no_visible_change",
        evidence={"reason": "observation did not change"},
    )


def test_verifier_reports_progress_when_expected_app_and_text_are_present() -> None:
    verifier = StepVerifier()
    before = _observation(screenshot_path="before.png", active_app="Codex")
    after = _observation(
        screenshot_path="after.png",
        active_app="Safari",
        window_title="Example Domain",
        ocr_texts=["Example Domain"],
    )

    result = verifier.verify(
        task_text="Open Safari and go to example.com",
        actions=[Action(kind="open_app", params={"name": "Safari"})],
        before=before,
        after=after,
    )

    assert result == VerificationResult(
        status="progress",
        failure_category=None,
        evidence={
            "matched_text": "Example Domain",
            "matched_window_title": "Example Domain",
            "matched_app": "Safari",
        },
    )


def test_verifier_reports_complete_when_goal_evidence_is_satisfied() -> None:
    verifier = StepVerifier()
    after = _observation(
        screenshot_path="after.png",
        active_app="Safari",
        window_title="Example Domain",
        ocr_texts=["Example Domain"],
    )

    result = verifier.verify(
        task_text="Open Safari and go to example.com",
        actions=[Action(kind="done", params={})],
        before=None,
        after=after,
    )

    assert result == VerificationResult(
        status="complete",
        failure_category=None,
        evidence={
            "matched_text": "Example Domain",
            "matched_window_title": "Example Domain",
            "matched_app": "Safari",
        },
    )


def test_verifier_does_not_mark_browser_task_complete_on_app_match_alone() -> None:
    verifier = StepVerifier()
    after = _observation(
        screenshot_path="after.png",
        active_app="Safari",
        window_title="YouTube",
        ocr_texts=[],
    )

    result = verifier.verify(
        task_text="Open Safari, go to YouTube, and search for asmr",
        actions=[Action(kind="done", params={})],
        before=None,
        after=after,
    )

    assert result == VerificationResult(
        status="progress",
        failure_category=None,
        evidence={"matched_app": "Safari"},
    )


def test_verifier_uses_window_title_as_browser_completion_evidence() -> None:
    verifier = StepVerifier()
    after = _observation(
        screenshot_path="after.png",
        active_app="Safari",
        window_title="YouTube - Search results for asmr",
        ocr_texts=[],
    )

    result = verifier.verify(
        task_text="Open Safari, go to YouTube, and search for asmr",
        actions=[Action(kind="done", params={})],
        before=None,
        after=after,
    )

    assert result == VerificationResult(
        status="complete",
        failure_category=None,
        evidence={
            "matched_window_title": "YouTube - Search results for asmr",
            "matched_app": "Safari",
        },
    )


def test_verifier_treats_bare_go_to_as_browser_task_requiring_content_evidence() -> (
    None
):
    verifier = StepVerifier()
    after = _observation(
        screenshot_path="after.png",
        active_app="Safari",
        window_title="Safari Start Page",
        ocr_texts=[],
    )

    result = verifier.verify(
        task_text="Go to openai.com and zoom in",
        actions=[Action(kind="done", params={})],
        before=None,
        after=after,
    )

    assert result == VerificationResult(
        status="progress",
        failure_category=None,
        evidence={"matched_app": "Safari"},
    )
