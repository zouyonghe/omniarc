from pathlib import Path


def test_readme_exposes_public_usage_sections() -> None:
    content = Path("README.md").read_text(encoding="utf-8")
    intro, _, current_status = content.partition("## Current Status")
    intro_lines = [line.strip() for line in intro.splitlines() if line.strip()]
    current_status_lines = [
        line.strip()
        for line in current_status.splitlines()
        if line.strip().startswith("-")
    ]

    assert "Quick Start" in content
    assert "Current Status" in content
    assert "Use with Codex" in content
    assert "Use with OpenCode" in content
    assert "zoom" in content.lower()
    assert "python -m omniarc --serve" in content
    assert "uv run python -m omniarc --health-check" in content
    assert "examples/macos.page-zoom.json" in content
    assert "examples/macos.maps-zoom.json" in content
    assert "examples/macos.page-scroll.json" in content
    assert (
        intro_lines[1]
        == "macOS-first GUI agent runtime with a cross-platform architecture."
    )
    assert current_status_lines[0].startswith(
        "- MCP-hosted task execution is macOS-first"
    )
    assert (
        "whole-page zoom, visible page scroll, and map-content zoom flows are macOS-first"
        in current_status_lines[1]
    )
    assert "Windows currently focuses on dry-run" in current_status_lines[2]
    assert "phrase-based and intentionally narrow" in current_status
    assert "There is no visual assertion layer" in current_status
