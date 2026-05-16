import json

from model_tools import handle_function_call
from vesta_runtime import (
    append_ledger_entry,
    artifact_manifest_status,
    create_run,
    ledger_search,
    ledger_status,
    ledger_tail,
    record_artifact,
    run_status,
    set_current_run,
    write_finalization,
)


def test_vesta_state_readers_return_bounded_structured_state(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_state", workspace_path=tmp_path, run_id="run_state")
    report = tmp_path / "report.md"
    report.write_text("report", encoding="utf-8")
    record_artifact(
        path=str(report),
        artifact_type="report",
        expected_by="user_request",
        status="exists",
        session_id="session_state",
    )
    append_ledger_entry(
        entry_type="claim",
        title="State reader claim",
        statement="Vesta state readers avoid broad ledger reads.",
        refs=["ledger.md"],
        status="supported",
        materiality="high",
        next_action="Use run_status.",
        session_id="session_state",
    )
    write_finalization(
        objective="Expose state readers.",
        verification="Artifact exists and ledger has a supported claim.",
        session_id="session_state",
    )

    status = ledger_status(session_id="session_state")
    tail = ledger_tail(session_id="session_state", limit=10)
    search = ledger_search(query="state readers", session_id="session_state")
    manifest = artifact_manifest_status(session_id="session_state")
    run_state = run_status(session_id="session_state")

    assert status["ledger_path"] == str(run.ledger_path)
    assert status["entry_count"] >= 3
    assert any(entry.get("type") == "claim" for entry in tail["entries"])
    assert search["total_matching"] >= 1
    assert manifest["counts_by_status"]["exists"] == 1
    assert run_state["finalization_status"] == "accepted"
    assert run_state["artifacts"]["artifacts"][0]["status"] == "exists"


def test_vesta_state_reader_tools_update_active_run(tmp_path, monkeypatch):
    set_current_run(None)
    create_run(session_id="session_state_tool", workspace_path=tmp_path, run_id="run_state_tool")
    monkeypatch.setenv("HERMES_SESSION_ID", "session_state_tool")
    append_ledger_entry(
        entry_type="gap",
        title="Open gap",
        statement="One gap remains.",
        status="unresolved",
        materiality="medium",
        session_id="session_state_tool",
    )

    raw = handle_function_call("ledger_status", {"limit": 5}, session_id="session_state_tool")
    result = json.loads(raw)

    assert result["success"] is True
    assert result["counts_by_type"]["gap"] == 1
    assert result["gaps"][0]["statement"] == "One gap remains."
