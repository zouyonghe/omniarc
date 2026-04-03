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


def test_examples_readme_mentions_macos_and_windows_dry_run_flow() -> None:
    content = Path("examples/README.md").read_text(encoding="utf-8")
    assert "macOS dry-run" in content
    assert "Windows dry-run" in content
    assert "run_task" in content
    assert "resume_task" in content
