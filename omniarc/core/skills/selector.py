from __future__ import annotations

from omniarc.core.skills.schema import SkillSpec
from omniarc.runtimes.base.capabilities import CapabilitySet


def _matches_host(skill: SkillSpec, host: str | None) -> bool:
    return not host or not skill.hosts or host in skill.hosts


def _matches_platform(skill: SkillSpec, platform: str | None) -> bool:
    return not platform or not skill.platforms or platform in skill.platforms


def _matches_capabilities(skill: SkillSpec, capabilities: CapabilitySet | None) -> bool:
    if capabilities is None:
        return not skill.requires_capabilities
    return all(capabilities.supports(name) for name in skill.requires_capabilities)


def select_skills(
    skills: list[SkillSpec],
    *,
    host: str | None,
    platform: str | None,
    capabilities: CapabilitySet | None,
) -> list[SkillSpec]:
    selected = [
        skill
        for skill in skills
        if _matches_host(skill, host)
        and _matches_platform(skill, platform)
        and _matches_capabilities(skill, capabilities)
    ]
    return sorted(selected, key=lambda skill: skill.priority, reverse=True)
