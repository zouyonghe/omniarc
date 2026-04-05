from __future__ import annotations

from omniarc.core.models import PreplanResult, TaskSpec


class PreplanService:
    async def build(self, task: TaskSpec) -> PreplanResult:
        return self.build_sync(task)

    def build_sync(self, task: TaskSpec) -> PreplanResult:
        return PreplanResult(planning_mode="search" if task.allow_search else "direct")
