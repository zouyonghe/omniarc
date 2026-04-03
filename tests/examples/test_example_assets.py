import json
from pathlib import Path


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_macos_dry_run_example_config_is_complete() -> None:
    config = _load_json(Path("examples/macos.dry-run.json"))
    assert config["runtime"]["platform"] == "macos"
    assert config["runtime"]["dry_run"] is True
    assert config["agent"]["task"]


def test_windows_dry_run_example_config_is_complete() -> None:
    config = _load_json(Path("examples/windows.dry-run.json"))
    assert config["runtime"]["platform"] == "windows"
    assert config["runtime"]["dry_run"] is True
    assert config["agent"]["task"]


def test_page_zoom_example_config_is_complete() -> None:
    config = _load_json(Path("examples/macos.page-zoom.json"))
    assert config["runtime"]["platform"] == "macos"
    assert config["runtime"]["dry_run"] is True
    assert config["agent"]["task"] == "Open Safari and go to example.com and zoom in"


def test_maps_zoom_example_config_is_complete() -> None:
    config = _load_json(Path("examples/macos.maps-zoom.json"))
    assert config["runtime"]["platform"] == "macos"
    assert config["runtime"]["dry_run"] is True
    assert (
        config["agent"]["task"]
        == "Open Safari and go to google.com/maps/place/Washington and zoom in"
    )


def test_page_scroll_example_config_is_complete() -> None:
    config = _load_json(Path("examples/macos.page-scroll.json"))
    assert config["runtime"]["platform"] == "macos"
    assert config["runtime"]["dry_run"] is True
    assert (
        config["agent"]["task"]
        == "Open Safari and go to en.wikipedia.org/wiki/Washington,_D.C. and scroll down"
    )


def test_examples_readme_mentions_macos_and_windows_dry_run_flow() -> None:
    content = Path("examples/README.md").read_text(encoding="utf-8")
    assert "macOS dry-run" in content
    assert "Windows dry-run" in content
    assert "run_task" in content
    assert "resume_task" in content
    assert "page zoom" in content
    assert "maps zoom" in content
    assert "page scroll" in content
    assert "examples/macos.page-zoom.json" in content
    assert "examples/macos.maps-zoom.json" in content
    assert "examples/macos.page-scroll.json" in content
    assert "whole page" in content
    assert "map content" in content
    assert "scroll down" in content
    assert '"task": "Open Safari and go to example.com"' in content
    assert "macOS-first today" in content
    assert "examples/windows.dry-run.json" in content
