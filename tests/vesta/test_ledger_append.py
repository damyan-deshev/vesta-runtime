import json

from model_tools import handle_function_call
from vesta_runtime import append_ledger_entry, create_run, set_current_run


def test_append_ledger_entry_adds_runtime_owned_metadata(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_ledger", workspace_path=tmp_path, run_id="run_ledger")

    result = append_ledger_entry(
        entry_type="decision",
        title="Use Markdown ledger",
        statement="The model-facing ledger is Markdown.",
        refs=["run.md"],
        status="accepted",
        materiality="high",
        next_action="Implement append primitive.",
        session_id="session_ledger",
    )

    ledger = run.ledger_path.read_text(encoding="utf-8")
    assert result["entry_id"].startswith("le_")
    assert "Use Markdown ledger" in ledger
    assert "- Type: `decision`" in ledger
    assert "- Materiality: `high`" in ledger
    assert "- Run ID: `run_ledger`" in ledger
    assert "- Hermes Session ID: `session_ledger`" in ledger
    assert "Implement append primitive." in ledger


def test_ledger_append_tool_writes_active_run(tmp_path, monkeypatch):
    set_current_run(None)
    run = create_run(session_id="session_tool", workspace_path=tmp_path, run_id="run_tool")
    monkeypatch.setenv("HERMES_SESSION_ID", "session_tool")

    raw = handle_function_call(
        "ledger_append",
        {
            "entry_type": "gap",
            "title": "Missing threshold decision",
            "statement": "The default broad-read threshold is not verified.",
            "materiality": "medium",
            "refs": ["config"],
        },
        session_id="session_tool",
    )

    result = json.loads(raw)
    assert result["success"] is True
    ledger = run.ledger_path.read_text(encoding="utf-8")
    assert "Missing threshold decision" in ledger
    assert "The default broad-read threshold is not verified." in ledger
