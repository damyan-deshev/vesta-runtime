import json

from model_tools import handle_function_call
from vesta_runtime import (
    append_ledger_entry,
    artifact_manifest_status,
    create_run,
    find_latest_run_for_session,
    ledger_search,
    ledger_status,
    ledger_tail,
    record_artifact,
    record_session_rotation,
    run_status,
    run_status_from_dir,
    set_current_run,
    write_finalization,
)


def test_vesta_state_readers_return_bounded_structured_state(tmp_path):
    set_current_run(None)
    run = create_run(
        session_id="session_state",
        workspace_path=tmp_path,
        run_id="run_state",
        model="Qwen3.6-27B-MTP-Q6_K",
        provider="custom:vesta-local-llama",
    )
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
    assert run_state["runtime"]["model"] == "Qwen3.6-27B-MTP-Q6_K"
    assert run_state["runtime"]["provider"] == "custom:vesta-local-llama"
    assert run_state["artifacts"]["artifacts"][0]["status"] == "exists"


def test_run_status_next_action_prefers_finalization_over_stale_ledger(tmp_path):
    set_current_run(None)
    run = create_run(
        session_id="session_final_next",
        workspace_path=tmp_path,
        run_id="run_final_next",
    )
    append_ledger_entry(
        entry_type="commitment",
        title="Seed eval contract",
        statement="Model must satisfy typed Vesta eval tool order before final response.",
        status="active",
        materiality="critical",
        next_action="Model must satisfy typed Vesta eval tool order before final response.",
        session_id="session_final_next",
    )

    write_finalization(
        objective="Finish run.",
        verification="No artifacts required.",
        session_id="session_final_next",
    )

    status = run_status(session_id="session_final_next")

    assert status["finalization_status"] == "accepted"
    assert status["next_action"] == "none"
    assert "Latest Next Action: none" in run.control_plane_path.read_text(encoding="utf-8")


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


def test_vesta_status_can_be_read_from_existing_run_dir(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_status_dir", workspace_path=tmp_path, run_id="run_status_dir")
    write_finalization(
        objective="Read status from run dir.",
        verification="No artifacts required.",
        session_id="session_status_dir",
    )
    set_current_run(None)

    status = run_status_from_dir(run.run_dir)

    assert status is not None
    assert status["run_id"] == "run_status_dir"
    assert status["finalization_status"] == "accepted"
    assert status["run_dir"] == str(run.run_dir)


def test_latest_vesta_run_lookup_follows_session_lineage(tmp_path):
    set_current_run(None)
    old = create_run(session_id="session_old", workspace_path=tmp_path, run_id="run_old")
    write_finalization(
        objective="Old run.",
        failures=["blocked"],
        session_id="session_old",
    )
    set_current_run(None)
    run = create_run(session_id="session_a", workspace_path=tmp_path, run_id="run_lookup")
    record_session_rotation(
        old_session_id="session_a",
        new_session_id="session_b",
        reason="compression",
    )
    write_finalization(
        objective="Lookup latest run.",
        verification="Done.",
        session_id="session_b",
    )
    set_current_run(None)

    status = find_latest_run_for_session("session_b")

    assert status is not None
    assert status["run_id"] == run.run_id
    assert status["matched_session_id"] == "session_b"
    assert status["finalization_status"] == "accepted"
    assert status["lineage"]["hermes_session_id"] == "session_a"
