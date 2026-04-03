# OmniArc

A Host-Neutral, Cross-Platform GUI Agent Runtime.

OmniArc is a specialized runtime for GUI automation agents, designed to bridge the gap between high-level reasoning (LLMs) and low-level platform execution. It provides a robust, typed state machine, durable run storage, and a flexible skill system via Markdown.

## 🌟 Features

- **Typed Core State Machine**: A well-defined lifecycle (Plan → Observe → Decide → Act → Execute → Record) ensuring reliable agent behavior.
- **Cross-Platform Runtimes**: Native support for **macOS** and **Windows**, with explicit dry-run modes for safe testing.
- **Durable Execution**: All runs are persisted in `.omniarc/runs/`, allowing for **pause, resume, and replay**.
- **Markdown-Based Skills**: Reusable agent instructions with YAML frontmatter for capability-based selection.
- **MCP Integration**: First-class support for the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/), compatible with Codex, OpenCode, Claude Desktop, and more.
- **Artifact Management**: Automatic capture of screenshots, action logs, and step-by-step memory.

## 🏗️ Architecture

OmniArc follows a modular architecture where the `OmniArcAgent` orchestrates several specialized components:

- **Planner**: Generates initial execution strategies based on task specifications.
- **Observer**: Captures the current system state (e.g., screenshots, accessibility trees).
- **Brain**: Evaluates observations against the plan to make the next decision.
- **Actor**: Translates decisions into specific platform actions (e.g., `open_app`, `type_text`, `hotkey`).
- **Executor**: Performs the actual UI interactions via platform-specific runtimes.
- **Memory**: Records every step for durability and future reflection.

## 🛠️ Installation

```bash
# Create a virtual environment
uv venv .venv
source .venv/bin/activate

# Install in editable mode
uv pip install -e .

# Run tests
pytest -v
```

## 🚀 Usage

### Running Locally (Direct Config)

Execute tasks directly using JSON configuration files:

```bash
python -m omniarc --config examples/macos.dry-run.json
python -m omniarc --config examples/windows.dry-run.json
```

### Running as an MCP Server

OmniArc can be used as a tool provider for any MCP-compatible host:

```bash
python -m omniarc --serve
```

#### Registering with Hosts

**Codex:**
```bash
codex mcp add omniarc -- python -m omniarc.integrations.mcp.server
```

**OpenCode (`config.json`):**
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

## 📜 Skills System

OmniArc uses Markdown files in `skills/` to define agent behaviors. Each skill includes YAML metadata to help the runtime select the right tool for the job:

```markdown
---
name: browser-basics
tags: [browser, navigation]
platforms: [macos, windows]
requires_capabilities: [screen_capture]
---
Prefer direct address-bar navigation for known URLs...
```

## 📂 Project Layout

- `omniarc/core/`: The central state machine and component interfaces.
- `omniarc/runtimes/`: Platform-specific implementations (macOS, Windows).
- `omniarc/integrations/`: MCP server and external host bridges.
- `skills/`: Markdown-based agent instructions.
- `examples/`: Sample configurations and dry-run demos.
- `tests/`: Comprehensive test suite for all components.

## 🤝 Contributing

We welcome contributions! Please ensure all PRs include tests and adhere to the established architectural patterns.

## 📄 License

MIT
