from omniarc.integrations.openclaw.export import build_codex_mcp_config


def test_build_codex_mcp_config_mentions_omniarc_server() -> None:
    config = build_codex_mcp_config("/tmp/omniarc/.venv/bin/python")
    assert "omniarc.integrations.mcp.server" in config
