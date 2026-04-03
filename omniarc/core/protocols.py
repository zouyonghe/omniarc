from __future__ import annotations

from typing import Protocol

from omniarc.core.models import Action, ActionResult, Observation
from omniarc.runtimes.base.capabilities import CapabilitySet


class RuntimeObserver(Protocol):
    async def observe(self) -> Observation: ...


class RuntimeExecutor(Protocol):
    async def execute(self, actions: list[Action]) -> list[ActionResult]: ...


class CapabilityProvider(Protocol):
    def get_capabilities(self) -> CapabilitySet: ...


class PermissionChecker(Protocol):
    def ensure_ready(self) -> None: ...
