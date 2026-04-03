from __future__ import annotations

from pydantic import Field

from omniarc.core.models import OmniArcModel


class SkillSpec(OmniArcModel):
    name: str
    description: str
    version: int = 1
    tags: list[str] = Field(default_factory=list)
    stages: list[str] = Field(default_factory=list)
    platforms: list[str] = Field(default_factory=list)
    hosts: list[str] = Field(default_factory=list)
    requires_capabilities: list[str] = Field(default_factory=list)
    priority: int = 0
    body: str = ""
    source_path: str | None = None
