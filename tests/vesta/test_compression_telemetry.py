import logging
import os

from run_agent import AIAgent


def _agent() -> AIAgent:
    return AIAgent(
        model="test/model",
        provider="test",
        api_key="test",
        base_url="http://localhost:9/v1",
        quiet_mode=True,
        skip_memory=True,
        enabled_toolsets=[],
    )


def test_compression_check_logs_decision_inputs(caplog):
    agent = _agent()

    with caplog.at_level(logging.INFO):
        decision = agent._compression_check_decision(
            current_tokens=1,
            phase="unit_test",
            api_call_count=1,
        )

    assert decision["trigger"] is False
    assert decision["threshold_tokens"] == agent.context_compressor.threshold_tokens
    assert decision["compressor_context_length"] == agent.context_compressor.context_length
    assert "Compression check: phase=unit_test" in caplog.text
    assert "threshold_tokens=" in caplog.text
    assert "current_tokens=1" in caplog.text


def test_force_compression_next_hook_triggers_without_large_prompt(monkeypatch):
    agent = _agent()
    monkeypatch.setenv("VESTA_FORCE_COMPRESSION_NEXT", "1")

    decision = agent._compression_check_decision(
        current_tokens=1,
        phase="unit_test",
        api_call_count=1,
    )

    assert decision["trigger"] is True
    assert decision["reason"] == "VESTA_FORCE_COMPRESSION_NEXT=1 at unit_test"
    assert os.getenv("VESTA_FORCE_COMPRESSION_NEXT") == "0"
