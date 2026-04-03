from __future__ import annotations

from pathlib import Path

import yaml

from omniarc.core.skills.schema import SkillSpec


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text

    lines = text.splitlines()
    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break

    if end_index is None:
        return {}, text

    frontmatter = "\n".join(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :]).strip()
    return yaml.safe_load(frontmatter) or {}, body


def load_skills(path: Path) -> list[SkillSpec]:
    skills: list[SkillSpec] = []
    for file_path in sorted(path.glob("*.md")):
        text = file_path.read_text(encoding="utf-8")
        metadata, body = _split_frontmatter(text)
        skills.append(SkillSpec(**metadata, body=body, source_path=str(file_path)))
    return skills
