# OmniArc

macOS-first GUI agent runtime with a cross-platform architecture.

OmniArc sits between an LLM host and the desktop it needs to control. It gives agent runs a typed lifecycle, durable artifacts, platform-specific executors, and an MCP server surface that tools like Codex and OpenCode can call.

## Why OmniArc Exists

Most GUI automation experiments mix planning, desktop control, and run state in one place. OmniArc separates those concerns:

- `core` handles planning, decisions, actions, and durable run state
- `runtimes` handle platform-specific observation and execution
- `integrations` expose the runtime through MCP and host adapters

That makes it easier to test dry-run flows, inspect artifacts, and evolve platform support without rewriting the whole agent loop.

## Current Capabilities

- Typed run lifecycle with persisted `status.json`, `checkpoint.json`, `actions.jsonl`, and `memory.jsonl`
- macOS and Windows runtime entry points with dry-run support
- MCP server for `run_task`, `resume_task`, `pause_task`, `inspect_run`, `replay_run`, and artifact retrieval
- Independent LLM Support through provider-based planning fallback and verification hooks
- Markdown skill loading from `skills/`
- Narrow deterministic planner coverage for browser navigation, whole-page zoom, visible page scroll, and Google Maps map-content zoom flows
- macOS scroll support with direction, repeat count, and optional modifier keys

## Quick Start

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e .
uv run python -m omniarc --health-check
```

Run a local config directly:

```bash
python -m omniarc --config examples/macos.dry-run.json
python -m omniarc --config examples/macos.page-zoom.json
python -m omniarc --config examples/macos.maps-zoom.json
python -m omniarc --config examples/macos.page-scroll.json
```

If you want the Windows dry-run path, run:

```bash
python -m omniarc --config examples/windows.dry-run.json
```

## Run As An MCP Server

```bash
python -m omniarc --serve
```

The server exposes health, run lifecycle, replay, and artifact inspection tools over stdio MCP.

`run_task` and `resume_task` now default to real execution (`dry_run=false`). Use the MCP server as a macOS-first execution path today; use direct config execution for Windows dry-run flows.

## Independent LLM Support

OmniArc now has an internal provider-based LLM layer for planning fallback, recovery, and the `fast-verified` execution profile.

- Supported provider protocols today:
  - `OpenAI`
  - `OpenAI-compatible`
  - `Anthropic`
- Example provider config: `examples/llm_endpoints.example.json`
- Recommended local config path: `examples/llm_endpoints.json` (gitignored)
- MCP tool parameters:
  - `llm_config_path`
  - `llm_profile`

The default autonomous profile direction is `fast-verified`: execute quickly, then verify and recover using separate reasoning.

## Use with Codex

Register OmniArc as a local MCP server:

```bash
codex mcp add omniarc -- python -m omniarc.integrations.mcp.server
```

Typical task prompts that the current planner understands well:

- `Open Safari and go to example.com`
- `Open Safari and go to example.com and zoom in`
- `Open Safari and go to en.wikipedia.org/wiki/Washington,_D.C. and scroll down`
- `Open Safari and zoom out`
- `Open Safari and go to google.com/maps/place/Washington and zoom in`

When an internal LLM config is provided through `llm_config_path`, unsupported natural-language phrases can be validated and planned through LLM fallback instead of failing at the rule-planner boundary. The intended workflow is to copy `examples/llm_endpoints.example.json` to the local ignored file `examples/llm_endpoints.json`, then point OmniArc at that local file.

## Use with OpenCode

Add this to `config.json`:

```json
{
  "mcp": {
    "omniarc": {
      "type": "local",
      "command": ["python", "-m", "omniarc.integrations.mcp.server"],
      "enabled": true
    }
  }
}
```

## Examples

- `examples/macos.dry-run.json`: basic macOS dry-run flow
- `examples/macos.page-zoom.json`: Safari navigation plus whole-page zoom
- `examples/macos.page-scroll.json`: Safari navigation plus visible page scroll
- `examples/macos.maps-zoom.json`: Google Maps navigation plus map-content zoom
- `examples/llm_endpoints.example.json`: example provider config for internal LLM routing
- `examples/llm_endpoints.json`: local gitignored provider config path for your real credentials
- `examples/windows.dry-run.json`: Windows dry-run flow

See `examples/README.md` for runnable example details.

## Current Status

OmniArc is early but usable for local evaluation.

- MCP-hosted task execution is macOS-first today because `run_task` builds macOS runtime configs by default.
- Current whole-page zoom, visible page scroll, and map-content zoom flows are macOS-first behaviors, not general cross-platform capabilities.
- Windows currently focuses on dry-run behavior and contract coverage rather than a complete real-input backend
- macOS has the fuller execution path today, including MCP-hosted task launches, whole-page zoom, and map-content zoom
- Planner coverage is still phrase-based and intentionally narrow; this is not yet a general natural-language desktop agent
- There is no visual assertion layer that proves a page or map actually zoomed after execution

## Development Notes

Project layout:

- `omniarc/core/`: planner, brain, agent loop, models, state
- `omniarc/runtimes/`: macOS and Windows runtime implementations
- `omniarc/integrations/`: MCP server and host bridges
- `examples/`: direct-run configs and demo scenarios
- `tests/`: unit and integration coverage

Useful commands:

```bash
uv run pytest -q
uv run pytest tests/core/test_planner.py -v
uv run pytest tests/runtimes/macos/test_executor.py -v
uv run python -m omniarc --health-check
```

## License

MIT
