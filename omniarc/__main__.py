from __future__ import annotations

import argparse
import json
from pathlib import Path

from omniarc.integrations.mcp.server import health_check, main as run_server
from omniarc.runtime_runner import run_from_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OmniArc tools and MCP server.")
    parser.add_argument("--serve", action="store_true", help="Run the stdio MCP server")
    parser.add_argument(
        "--health-check", action="store_true", help="Print runtime health as JSON"
    )
    parser.add_argument("--config", default=None, help="Runtime config path")
    args = parser.parse_args()

    if args.health_check:
        print(json.dumps(health_check(), ensure_ascii=False))
        return

    if args.serve or args.config is None:
        run_server()
        return

    state = run_from_config(Path(args.config))
    print(state.model_dump_json())


if __name__ == "__main__":
    main()
