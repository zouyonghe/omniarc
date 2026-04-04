from pathlib import Path


def test_readme_documents_llm_setup_and_fast_verified_mode() -> None:
    content = Path("README.md").read_text(encoding="utf-8")

    assert "Independent LLM Support" in content
    assert "fast-verified" in content
    assert "OpenAI" in content
    assert "OpenAI-compatible" in content
    assert "Anthropic" in content
    assert "examples/llm_endpoints.example.json" in content
    assert "examples/llm_endpoints.json" in content
    assert "llm_config_path" in content


def test_examples_readme_mentions_llm_endpoint_config() -> None:
    content = Path("examples/README.md").read_text(encoding="utf-8")

    assert "llm_endpoints.example.json" in content
    assert "llm_endpoints.json" in content
    assert "defaults to real execution" in content
    assert "fast-verified" in content
