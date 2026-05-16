import json

from model_tools import handle_function_call
from vesta_runtime import create_run, record_artifact, set_current_run, write_finalization


def test_missing_artifact_blocks_finalization(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_final", workspace_path=tmp_path, run_id="run_final")
    record_artifact(
        path="reports/audit.md",
        artifact_type="report",
        expected_by="user_request",
        status="expected",
        impact_if_missing="User asked for the report.",
        session_id="session_final",
    )

    result = write_finalization(
        objective="Produce audit report.",
        verification="Manual inspection pending.",
        session_id="session_final",
    )

    assert result["verdict"] == "blocked"
    assert "missing_artifacts" in result["blockers"]
    finalization = run.finalization_path.read_text(encoding="utf-8")
    assert "reports/audit.md" in finalization
    assert "Resolve finalization blockers." in finalization


def test_existing_artifact_with_skip_reason_can_finalize_non_code(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_final", workspace_path=tmp_path, run_id="run_final_exists")
    artifact = tmp_path / "plan.md"
    artifact.write_text("plan", encoding="utf-8")
    record_artifact(
        path=str(artifact),
        artifact_type="plan",
        expected_by="model_commitment",
        status="exists",
        session_id="session_final",
    )

    result = write_finalization(
        objective="Produce plan.",
        skip_reason="Non-code planning output; no tests required.",
        gaps=["One follow-up decision remains."],
        session_id="session_final",
    )

    assert result["verdict"] == "accepted_with_gaps"
    finalization = run.finalization_path.read_text(encoding="utf-8")
    assert "Non-code planning output" in finalization
    assert "One follow-up decision remains." in finalization


def test_artifact_and_finalize_tools_update_active_run(tmp_path, monkeypatch):
    set_current_run(None)
    run = create_run(session_id="session_final_tool", workspace_path=tmp_path, run_id="run_final_tool")
    monkeypatch.setenv("HERMES_SESSION_ID", "session_final_tool")

    artifact_raw = handle_function_call(
        "artifact_record",
        {
            "path": "handoff.md",
            "artifact_type": "handoff",
            "expected_by": "user_request",
            "status": "missing",
        },
        session_id="session_final_tool",
    )
    artifact_result = json.loads(artifact_raw)
    assert artifact_result["success"] is True

    final_raw = handle_function_call(
        "finalize_run",
        {
            "objective": "Export handoff.",
            "verification": "Checked manifest.",
        },
        session_id="session_final_tool",
    )
    final_result = json.loads(final_raw)

    assert final_result["success"] is True
    assert final_result["verdict"] == "blocked"
    assert "handoff.md" in run.finalization_path.read_text(encoding="utf-8")
    assert "handoff.md" in run.artifact_manifest_path.read_text(encoding="utf-8")
