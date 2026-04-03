from omniarc.integrations.mcp.server import list_tool_names


def test_server_exposes_expected_tools() -> None:
    assert list_tool_names() == [
        "health_check",
        "get_runtime_info",
        "list_skills",
        "validate_task",
        "run_task",
        "resume_task",
        "get_task_status",
        "pause_task",
        "inspect_run",
        "replay_run",
        "cancel_task",
        "get_run_artifact",
    ]
