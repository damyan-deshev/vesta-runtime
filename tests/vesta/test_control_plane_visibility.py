import json

from model_tools import handle_function_call
from vesta_runtime import (
    create_run,
    record_validator_result,
    record_worker_state,
    set_current_run,
    write_control_plane_snapshot,
    write_finalization,
)


def test_control_plane_snapshot_reads_vesta_artifacts(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_control", workspace_path=tmp_path, run_id="run_control")
    record_worker_state(
        worker_id="worker_audit",
        objective="Audit report.",
        status="completed",
        model_lane="delegation.fast_worker",
        parent_acceptance="accepted",
        spot_audit="No material worker claims.",
        session_id="session_control",
    )
    record_validator_result(
        trigger="manual smoke",
        scope="final report",
        mode="skipped",
        status="skipped",
        skip_reason="No validator lane configured.",
        session_id="session_control",
    )
    write_finalization(
        objective="Finalize control-plane smoke.",
        verification="Tests passed.",
        session_id="session_control",
    )

    result = write_control_plane_snapshot(
        session_id="session_control",
        next_action="Ship handoff.",
    )

    assert result["finalization_status"] == "accepted"
    assert result["validator_status"] == "skipped"
    snapshot = run.control_plane_path.read_text(encoding="utf-8")
    assert f"Run Path: `{run.run_dir}`" in snapshot
    assert f"Ledger Path: `{run.ledger_path}`" in snapshot
    assert "worker_audit" in snapshot
    assert "Finalization Status: `accepted`" in snapshot
    assert "Validator Status: `skipped`" in snapshot
    assert "Latest Next Action: Ship handoff." in snapshot
    assert "downstream snapshot, not authoritative runtime state" in snapshot


def test_control_plane_snapshot_does_not_infer_success_without_finalization(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_control_missing", workspace_path=tmp_path, run_id="run_control_missing")

    result = write_control_plane_snapshot(session_id="session_control_missing")

    assert result["finalization_status"] == "not_written"
    snapshot = run.control_plane_path.read_text(encoding="utf-8")
    assert "Finalization Status: `not_written`" in snapshot
    assert "Finalization Status: `accepted`" not in snapshot


def test_finalize_run_refreshes_control_plane_snapshot(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_control_auto", workspace_path=tmp_path, run_id="run_control_auto")

    result = write_finalization(
        objective="Finalize and refresh control plane.",
        verification="No artifacts required.",
        session_id="session_control_auto",
    )

    assert result["verdict"] == "accepted"
    assert result["control_plane_path"] == str(run.control_plane_path)
    snapshot = run.control_plane_path.read_text(encoding="utf-8")
    assert "Snapshot Status: `not_generated`" not in snapshot
    assert "Finalization Status: `accepted`" in snapshot
    assert "Primary Hermes Session ID: `session_control_auto`" in snapshot


def test_control_plane_snapshot_tool_updates_active_run(tmp_path, monkeypatch):
    set_current_run(None)
    run = create_run(session_id="session_control_tool", workspace_path=tmp_path, run_id="run_control_tool")
    monkeypatch.setenv("HERMES_SESSION_ID", "session_control_tool")

    raw = handle_function_call(
        "control_plane_snapshot",
        {"next_action": "Review finalization."},
        session_id="session_control_tool",
    )
    result = json.loads(raw)

    assert result["success"] is True
    assert result["finalization_status"] == "not_written"
    snapshot = run.control_plane_path.read_text(encoding="utf-8")
    assert "Review finalization." in snapshot
