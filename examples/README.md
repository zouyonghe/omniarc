# Examples

This directory contains runnable examples for direct config execution and MCP-driven usage.

## Files

- `config.example.json`: generic starter config
- `macos.dry-run.json`: macOS dry-run config for local runner testing
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

### Example `run_task` payload for macOS dry-run

```json
{
  "task": "Open Safari and navigate to example.com",
  "max_steps": 3,
  "dry_run": true,
  "artifacts_dir": ".omniarc"
}
```

### Example `run_task` payload for Windows dry-run

```json
{
  "task": "Open Notepad and type a short note",
  "max_steps": 3,
  "dry_run": true,
  "artifacts_dir": ".omniarc"
}
```

### Example `resume_task` payload

```json
{
  "agent_id": "macos-dry-run-demo",
  "dry_run": true,
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
