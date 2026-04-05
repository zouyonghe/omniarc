from __future__ import annotations

import pytest
from pydantic import ValidationError

from omniarc.core.composite_planner import CompositePlanner
from omniarc.core.models import PlanBundle, PlanStep, PreplanResult, TaskSpec
from omniarc.core.planner import Planner


class UnsupportedPlanner(Planner):
    async def plan(self, task: TaskSpec) -> dict:
        return self._unsupported_plan(task)

    def plan_sync(self, task: TaskSpec) -> dict:
        return self._unsupported_plan(task)


class FakePreplanService:
    def __init__(self, result: PreplanResult | Exception) -> None:
        self.result = result
        self.calls: list[TaskSpec] = []

    async def build(self, task: TaskSpec) -> PreplanResult:
        self.calls.append(task)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    def build_sync(self, task: TaskSpec) -> PreplanResult:
        self.calls.append(task)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakePlannerService:
    def __init__(self, result: PlanBundle | dict) -> None:
        self.result = result
        self.calls: list[tuple[TaskSpec, PreplanResult]] = []

    async def build(self, task: TaskSpec, preplan: PreplanResult):
        self.calls.append((task, preplan))
        return self.result

    def build_sync(self, task: TaskSpec, preplan: PreplanResult):
        self.calls.append((task, preplan))
        return self.result


@pytest.mark.asyncio
async def test_composite_planner_keeps_rule_plan_for_simple_supported_task() -> None:
    preplan_service = FakePreplanService(PreplanResult(planning_mode="search"))
    planner_service = FakePlannerService(
        PlanBundle(summary="unused", status="supported", source="planner")
    )
    planner = CompositePlanner(
        rule_planner=Planner(),
        preplan_service=preplan_service,
        planner_service=planner_service,
    )

    plan = await planner.plan(TaskSpec(task="Open Finder"))

    assert plan.status == "supported"
    assert plan.source == "rule"
    assert [step.goal for step in plan.steps] == ["open_app", "wait", "done"]
    assert preplan_service.calls == []
    assert planner_service.calls == []


@pytest.mark.asyncio
async def test_composite_planner_returns_plan_bundle_from_preplan_pipeline() -> None:
    preplan_service = FakePreplanService(
        PreplanResult(planning_mode="search", selected_skills=["search"])
    )
    planner_service = FakePlannerService(
        PlanBundle(
            summary="Research OpenAI pricing",
            status="supported",
            source="planner",
            preplan=PreplanResult(planning_mode="search", selected_skills=["search"]),
            steps=[
                PlanStep(
                    goal="Open browser",
                    completion_hint="Browser is frontmost",
                    allowed_actions=["open_app"],
                )
            ],
        )
    )
    planner = CompositePlanner(
        rule_planner=UnsupportedPlanner(),
        preplan_service=preplan_service,
        planner_service=planner_service,
    )

    plan = await planner.plan(
        TaskSpec(task="Research OpenAI pricing", allow_search=True)
    )

    assert plan.status == "supported"
    assert plan.source == "planner"
    assert plan.preplan.selected_skills == ["search"]
    assert plan.steps[0].goal == "Open browser"


@pytest.mark.asyncio
async def test_composite_planner_rejects_invalid_planner_payload() -> None:
    planner = CompositePlanner(
        rule_planner=UnsupportedPlanner(),
        preplan_service=FakePreplanService(PreplanResult(planning_mode="direct")),
        planner_service=FakePlannerService(
            {
                "summary": "broken",
                "status": "supported",
                "source": "planner",
                "steps": [{"completion_hint": "missing goal"}],
            }
        ),
    )

    plan = await planner.plan(TaskSpec(task="Do a complex thing"))

    assert plan.status == "unsupported_task"
    assert plan.source == "planner"
    assert plan.steps == []


@pytest.mark.asyncio
async def test_composite_planner_rejects_invalid_llm_action_kind() -> None:
    class FakeLLMClient:
        async def complete(self, request):
            class Response:
                content = '{"steps": [{"kind": "explode", "params": {}}]}'

            return Response()

        def complete_sync(self, request):
            class Response:
                content = '{"steps": [{"kind": "explode", "params": {}}]}'

            return Response()

    planner = CompositePlanner(
        rule_planner=UnsupportedPlanner(),
        preplan_service=FakePreplanService(PreplanResult(planning_mode="direct")),
        llm_client=FakeLLMClient(),
    )

    plan = await planner.plan(TaskSpec(task="Do a complex thing"))

    assert plan.status == "unsupported_task"
    assert plan.source == "planner"
    assert plan.steps == []


@pytest.mark.asyncio
async def test_composite_planner_preplan_failure_falls_back_only_for_rule_supported_task() -> (
    None
):
    planner = CompositePlanner(
        rule_planner=Planner(),
        preplan_service=FakePreplanService(RuntimeError("preplan unavailable")),
        planner_service=FakePlannerService(
            PlanBundle(summary="unused", status="supported", source="planner")
        ),
    )

    supported = await planner.plan(TaskSpec(task="Open Finder"))
    unsupported = await planner.plan(TaskSpec(task="Research OpenAI pricing"))

    assert supported.status == "supported"
    assert supported.source == "rule"
    assert unsupported.status == "unsupported_task"
    assert unsupported.source == "preplan"


def test_composite_planner_sync_rejects_invalid_planner_payload() -> None:
    planner = CompositePlanner(
        rule_planner=UnsupportedPlanner(),
        preplan_service=FakePreplanService(PreplanResult(planning_mode="direct")),
        planner_service=FakePlannerService(
            {
                "summary": "broken",
                "status": "supported",
                "source": "planner",
                "steps": [{"allowed_actions": ["open_app"]}],
            }
        ),
    )

    plan = planner.plan_sync(TaskSpec(task="Do a complex thing"))

    assert plan.status == "unsupported_task"
    assert plan.source == "planner"
    assert plan.steps == []
