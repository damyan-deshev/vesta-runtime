from vesta_runtime import (
    append_ledger_entry,
    create_run,
    record_session_rotation,
    set_current_run,
    write_resume_packet,
)


def test_write_resume_packet_includes_required_state(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_resume", workspace_path=tmp_path, run_id="run_resume")
    append_ledger_entry(
        entry_type="commitment",
        title="Write report",
        statement="The final report is still expected.",
        status="active",
        materiality="high",
        session_id="session_resume",
    )

    result = write_resume_packet(
        session_id="session_resume",
        objective="Finish the report.",
        current_phase="verification",
        next_action="Run final claim audit.",
        reason="test",
    )

    packet = run.resume_packet_path.read_text(encoding="utf-8")
    assert result["next_action"] == "Run final claim audit."
    assert "# Vesta Resume Packet" in packet
    assert "Finish the report." in packet
    assert "verification" in packet
    assert "Run final claim audit." in packet
    assert "Write report" in packet
    assert str(run.ledger_path) in packet


def test_session_rotation_writes_checkpoint_and_resume_packet(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_old", workspace_path=tmp_path, run_id="run_resume_rotation")

    record_session_rotation(
        old_session_id="session_old",
        new_session_id="session_new",
        reason="compression",
    )

    ledger = run.ledger_path.read_text(encoding="utf-8")
    packet = run.resume_packet_path.read_text(encoding="utf-8")
    assert "Hermes session rotated" in ledger
    assert "checkpoint" in ledger
    assert "Reason: `compression`" in packet
    assert "Hermes Session ID: `session_new`" in packet
    assert "Consult ledger and continue active work." in packet
