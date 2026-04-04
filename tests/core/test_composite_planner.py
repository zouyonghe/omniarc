from __future__ import annotations

import pytest

from omniarc.core.composite_planner import CompositePlanner
from omniarc.core.models import TaskSpec
from omniarc.llm.types import LLMResponse, ProviderError


class FakeLLMClient:
    def __init__(self, response: LLMResponse | None = None) -> None:
        self.calls: list[str] = []
        self.system_prompts: list[str | None] = []
        self.response = response

    async def complete(self, request):
        self.calls.append(request.prompt)
        self.system_prompts.append(request.system_prompt)
        if self.response is None:
            raise AssertionError("LLM client should not have been called")
        return self.response

    def complete_sync(self, request):
        self.calls.append(request.prompt)
        self.system_prompts.append(request.system_prompt)
        if self.response is None:
            raise AssertionError("LLM client should not have been called")
        return self.response


@pytest.mark.asyncio
async def test_composite_planner_uses_rule_plan_without_llm_fallback() -> None:
    llm_client = FakeLLMClient()
    planner = CompositePlanner(llm_client=llm_client)

    plan = await planner.plan(TaskSpec(task="Open Finder"))

    assert plan["status"] == "supported"
    assert plan["source"] == "rule"
    assert [step["kind"] for step in plan["steps"]] == ["open_app", "wait", "done"]
    assert llm_client.calls == []


@pytest.mark.asyncio
async def test_composite_planner_falls_back_to_llm_for_unsupported_task() -> None:
    llm_client = FakeLLMClient(
        response=LLMResponse(
            content='{"steps": [{"kind": "open_app", "params": {"name": "Safari"}}, {"kind": "done", "params": {}}]}',
            provider="openai_compatible",
            model="gpt-4o",
        )
    )
    planner = CompositePlanner(llm_client=llm_client)

    plan = await planner.plan(
        TaskSpec(task="Open Safari, go to YouTube, and search for asmr")
    )

    assert plan["status"] == "supported"
    assert plan["source"] == "llm"
    assert [step["kind"] for step in plan["steps"]] == ["open_app", "done"]
    assert llm_client.calls == ["Open Safari, go to YouTube, and search for asmr"]
    assert llm_client.system_prompts[0] is not None
    assert '"steps"' in llm_client.system_prompts[0]


@pytest.mark.asyncio
async def test_composite_planner_returns_unsupported_when_llm_produces_no_steps() -> (
    None
):
    llm_client = FakeLLMClient(
        response=LLMResponse(
            content='{"steps": []}',
            provider="openai_compatible",
            model="gpt-4o",
        )
    )
    planner = CompositePlanner(llm_client=llm_client)

    plan = await planner.plan(
        TaskSpec(task="Open Safari, go to YouTube, and search for asmr")
    )

    assert plan["status"] == "unsupported_task"
    assert plan["source"] == "llm"
    assert plan["steps"] == []


@pytest.mark.asyncio
async def test_composite_planner_rejects_malformed_llm_step_shapes() -> None:
    llm_client = FakeLLMClient(
        response=LLMResponse(
            content='{"steps": [{"foo": "bar"}]}',
            provider="openai_compatible",
            model="gpt-4o",
        )
    )
    planner = CompositePlanner(llm_client=llm_client)

    plan = await planner.plan(
        TaskSpec(task="Open Safari, go to YouTube, and search for asmr")
    )

    assert plan["status"] == "unsupported_task"
    assert plan["source"] == "llm"
    assert plan["steps"] == []


@pytest.mark.asyncio
async def test_composite_planner_returns_unsupported_when_llm_provider_fails() -> None:
    class FailingLLMClient:
        async def complete(self, request):
            raise ProviderError("endpoint failed")

        def complete_sync(self, request):
            raise ProviderError("endpoint failed")

    planner = CompositePlanner(llm_client=FailingLLMClient())

    plan = await planner.plan(
        TaskSpec(task="Open Safari, go to YouTube, and search for asmr")
    )

    assert plan["status"] == "unsupported_task"
    assert plan["source"] == "llm"
    assert plan["steps"] == []
