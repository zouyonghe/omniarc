from omniarc.integrations.mcp.bridge import build_runtime_config


def test_build_runtime_config_overrides_task_and_step_limit() -> None:
    config = build_runtime_config(
        base_config={"agent": {"task": "old", "max_steps": 5}},
        task="new",
        max_steps=9,
        resume=False,
        agent_id=None,
    )
    assert config["agent"]["task"] == "new"
    assert config["agent"]["max_steps"] == 9
