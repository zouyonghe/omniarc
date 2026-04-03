from pathlib import Path

from omniarc.core.skills.loader import load_skills
from omniarc.core.skills.selector import select_skills
from omniarc.runtimes.base.capabilities import CapabilitySet


def test_loader_parses_frontmatter_fixture() -> None:
    skills = load_skills(Path("tests/fixtures/skills"))
    assert skills[0].name == "browser-basics"


def test_selector_filters_by_capability() -> None:
    skills = load_skills(Path("tests/fixtures/skills"))
    selected = select_skills(
        skills,
        host="codex",
        platform="macos",
        capabilities=CapabilitySet(values={"screen_capture"}),
    )
    assert [skill.name for skill in selected] == ["browser-basics"]
