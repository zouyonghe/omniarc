from __future__ import annotations

import json


def build_codex_mcp_config(python_path: str) -> str:
    return f"codex mcp add omniarc -- {python_path} -m omniarc.integrations.mcp.server"


def build_opencode_config(python_path: str) -> dict:
    return {
        "$schema": "https://opencode.ai/config.json",
        "mcp": {
            "omniarc": {
                "type": "local",
                "command": [python_path, "-m", "omniarc.integrations.mcp.server"],
                "enabled": True,
            }
        },
    }


def build_claude_desktop_config(python_path: str) -> dict:
    return {
        "mcpServers": {
            "omniarc": {
                "command": python_path,
                "args": ["-m", "omniarc.integrations.mcp.server"],
            }
        }
    }


def build_openclaw_metadata(python_path: str) -> dict:
    return {
        "name": "omniarc",
        "command": [python_path, "-m", "omniarc.integrations.mcp.server"],
        "transport": "stdio",
    }


def dumps_json(payload: dict) -> str:
    return json.dumps(payload, indent=2)
