# Examples

This directory contains runnable examples for direct config execution and MCP-driven usage.

## Files

- `config.example.json`: generic starter config
- `macos.dry-run.json`: macOS dry-run config for local runner testing
- `macos.page-zoom.json`: macOS dry-run example for browser page zoom
- `macos.maps-zoom.json`: macOS dry-run example for Google Maps zoom
- `macos.page-scroll.json`: macOS dry-run example for visible page scroll
- `llm_endpoints.example.json`: example internal LLM provider configuration
- `llm_endpoints.json`: local gitignored copy of the provider config with your real credentials
- `windows.dry-run.json`: Windows dry-run config for local runner testing

## Direct Runner Examples

### macOS dry-run

```bash
.venv/bin/python -m omniarc --config examples/macos.dry-run.json
```

This writes artifacts under `.omniarc/runs/macos-dry-run-demo/` without attempting real desktop input.

### Windows dry-run

```bash
.venv/bin/python -m omniarc --config examples/windows.dry-run.json
```

This exercises the Windows runtime path in dry-run mode and writes artifacts under `.omniarc/runs/windows-dry-run-demo/`.

### macOS page zoom

```bash
.venv/bin/python -m omniarc --config examples/macos.page-zoom.json
```

Use this page zoom example when you want whole page zoom behavior in Safari. It exercises navigation plus the browser zoom hotkey path while keeping execution in dry-run mode.

### macOS maps zoom

```bash
.venv/bin/python -m omniarc --config examples/macos.maps-zoom.json
```

Use this maps zoom example when you want map content zoom behavior rather than whole page zoom. It opens a Google Maps location in Safari and simulates a scroll-based zoom-in path while staying in dry-run mode.

### macOS page scroll

```bash
.venv/bin/python -m omniarc --config examples/macos.page-scroll.json
```

Use this page scroll example when you want an obvious scroll down on a long document page. It opens a long Wikipedia article in Safari and sends a larger scroll action so the page visibly moves.

## MCP End-To-End Flow

Start the server:

```bash
.venv/bin/python -m omniarc --serve
```

Typical tool sequence for a host client:

1. `health_check`
2. `run_task`
3. `get_task_status`
4. `pause_task` or `resume_task` when needed
5. `inspect_run`
6. `replay_run`
7. `get_run_artifact`

### Example `run_task` payload for macOS real run

```json
{
  "task": "Open Safari and go to example.com",
  "max_steps": 3,
  "artifacts_dir": ".omniarc"
}
```

`run_task` is macOS-first today and defaults to real execution. Add `"dry_run": true` only when you explicitly want a non-interactive dry-run. For Windows dry-run evaluation, prefer the direct config path shown above with `examples/windows.dry-run.json`.

To enable internal LLM fallback and the `fast-verified` profile, copy `examples/llm_endpoints.example.json` to `examples/llm_endpoints.json`, fill in your real provider details there, and point MCP calls at that local ignored file with `llm_config_path`. The template now shows the distinct `openai` provider shape; `openai_compatible` remains supported for compatible backends.

Example:

```json
{
  "task": "Open Safari, go to YouTube, and search for asmr",
  "llm_config_path": "examples/llm_endpoints.json",
  "llm_profile": "fast-verified",
  "artifacts_dir": ".omniarc"
}
```

### Example `resume_task` payload

```json
{
  "agent_id": "macos-dry-run-demo",
  "artifacts_dir": ".omniarc"
}
```

## Artifact Inspection

After any run, inspect:

- `status.json` for current state
- `checkpoint.json` for resumable state
- `actions.jsonl` for replayable actions
- `memory.jsonl` for step summaries
- `observations/latest.png` for the latest captured screenshot
