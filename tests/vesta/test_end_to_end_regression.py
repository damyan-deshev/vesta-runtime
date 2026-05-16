import json
from pathlib import Path

from model_tools import handle_function_call
from vesta_runtime import (
    append_ledger_entry,
    capture_raw_output,
    create_run,
    record_artifact,
    record_session_rotation,
    set_current_run,
    write_control_plane_snapshot,
    write_finalization,
    write_handoff,
)
from vesta_runtime.retrieval import evaluate_read, reset_locator_history


def test_handoff_is_generated_from_vesta_files(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_handoff", workspace_path=tmp_path, run_id="run_handoff")
    append_ledger_entry(
        entry_type="decision",
        title="Use Markdown ledger",
        statement="Vesta handoff is generated from durable Markdown run files.",
        status="accepted",
        materiality="high",
        session_id="session_handoff",
    )
    append_ledger_entry(
        entry_type="claim",
        title="Tests pass",
        statement="The Vesta v0 regression path has test coverage.",
        status="supported",
        materiality="high",
        refs=["tests/vesta/test_end_to_end_regression.py"],
        session_id="session_handoff",
    )
    capture_raw_output(
        content="verification output",
        source="pytest",
        tool_use_id="tool_verification",
        session_id="session_handoff",
    )
    artifact = tmp_path / "report.md"
    artifact.write_text("report", encoding="utf-8")
    record_artifact(
        path=str(artifact),
        artifact_type="report",
        expected_by="user_request",
        status="exists",
        session_id="session_handoff",
    )
    write_finalization(
        objective="Produce handoff.",
        verification="Regression path passed.",
        session_id="session_handoff",
    )
    write_control_plane_snapshot(
        session_id="session_handoff",
        next_action="Continue implementation from handoff.",
    )

    result = write_handoff(
        objective="Produce Vesta v0 runtime handoff.",
        completed_work=["Implemented file-backed run state."],
        next_action="Continue implementation from handoff.",
        session_id="session_handoff",
    )

    assert result["finalization_status"] == "accepted"
    handoff = run.handoff_path.read_text(encoding="utf-8")
    assert "Source: Vesta run files, not transcript memory." in handoff
    assert "Vesta handoff is generated from durable Markdown run files." in handoff
    assert "The Vesta v0 regression path has test coverage." in handoff
    assert "tool_verification.txt" in handoff
    assert "Finalization Status: `accepted`" in handoff
    assert handoff.count("## Next Action") == 1
    assert "Continue implementation from handoff." in handoff


def test_end_to_end_regression_path_exercises_v0_critical_flow(tmp_path):
    set_current_run(None)
    reset_locator_history()
    run = create_run(session_id="session_e2e_old", workspace_path=tmp_path, run_id="run_e2e")
    source = tmp_path / "large.py"
    source.write_text("\n".join(f"line {idx}" for idx in range(300)), encoding="utf-8")

    append_ledger_entry(
        entry_type="decision",
        title="Regression path",
        statement="End-to-end regression must cover Vesta v0 critical path.",
        status="accepted",
        materiality="critical",
        session_id="session_e2e_old",
    )
    raw = capture_raw_output(
        content="raw evidence",
        source="terminal",
        tool_use_id="tool_evidence",
        session_id="session_e2e_old",
    )
    retrieval = evaluate_read(
        task_id="task_e2e",
        path=str(source),
        resolved_path=str(source),
        offset=0,
        limit=250,
    )
    assert retrieval["allowed"] is False
    record_session_rotation(
        old_session_id="session_e2e_old",
        new_session_id="session_e2e_new",
        reason="compression",
    )
    artifact = tmp_path / "artifact.md"
    artifact.write_text("done", encoding="utf-8")
    record_artifact(
        path=str(artifact),
        artifact_type="handoff",
        expected_by="model_commitment",
        status="exists",
        session_id="session_e2e_new",
    )
    finalization = write_finalization(
        objective="Exercise v0 regression.",
        verification=f"Checked raw ref {raw['raw_ref']} and retrieval gate.",
        session_id="session_e2e_new",
    )
    assert finalization["verdict"] == "accepted"
    handoff = write_handoff(
        objective="Exercise v0 regression.",
        completed_work=["Run creation", "Ledger append", "Raw ref", "Retrieval gate", "Compaction", "Finalization"],
        next_action="Review generated handoff.",
        session_id="session_e2e_new",
    )

    assert Path(handoff["handoff_path"]).exists()
    handoff_text = Path(handoff["handoff_path"]).read_text(encoding="utf-8")
    assert "Review generated handoff." in handoff_text
    assert "raw/tool_evidence.txt" in handoff_text
    assert "Finalization Status: `accepted`" in handoff_text
    assert run.resume_packet_path.exists()


def test_handoff_generate_tool_updates_active_run(tmp_path, monkeypatch):
    set_current_run(None)
    run = create_run(session_id="session_handoff_tool", workspace_path=tmp_path, run_id="run_handoff_tool")
    monkeypatch.setenv("HERMES_SESSION_ID", "session_handoff_tool")
    write_finalization(
        objective="Generate handoff.",
        verification="Manual verification.",
        session_id="session_handoff_tool",
    )

    raw = handle_function_call(
        "handoff_generate",
        {
            "objective": "Generate handoff.",
            "completed_work": ["Created finalization."],
            "next_action": "Read handoff.",
        },
        session_id="session_handoff_tool",
    )
    result = json.loads(raw)

    assert result["success"] is True
    assert result["next_action"] == "Read handoff."
    handoff = run.handoff_path.read_text(encoding="utf-8")
    assert "Created finalization." in handoff
