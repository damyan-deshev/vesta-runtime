import json

from model_tools import handle_function_call
from vesta_runtime import create_run, record_worker_state, set_current_run, write_finalization


def test_worker_state_records_requested_and_accepted_states(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_worker", workspace_path=tmp_path, run_id="run_worker")

    record_worker_state(
        worker_id="worker_pi",
        objective="Audit Pi benchmark behavior.",
        status="requested",
        model_lane="delegation.default",
        output_contract={"expected_artifact": "reports/pi.md"},
        session_id="session_worker",
    )
    record_worker_state(
        worker_id="worker_pi",
        objective="Audit Pi benchmark behavior.",
        status="accepted",
        model_lane="delegation.default",
        child_session_id="session_child",
        output_contract={"expected_artifact": "reports/pi.md"},
        session_id="session_worker",
    )

    worker_state = run.worker_state_path.read_text(encoding="utf-8")
    assert "worker_pi - requested" in worker_state
    assert "worker_pi - accepted" in worker_state
    assert "Child Session ID: `session_child`" in worker_state
    assert "delegation.default" in worker_state


def test_worker_state_tool_redacts_secret_metadata(tmp_path, monkeypatch):
    set_current_run(None)
    run = create_run(session_id="session_worker_tool", workspace_path=tmp_path, run_id="run_worker_tool")
    monkeypatch.setenv("HERMES_SESSION_ID", "session_worker_tool")

    raw = handle_function_call(
        "worker_state_record",
        {
            "worker_id": "worker_secret",
            "objective": "Run delegated check.",
            "status": "running",
            "model_lane": "provider=qwen api_key=sk-secret123456",
            "output_contract": {
                "expected_artifact": "reports/secret.md",
                "api_key": "sk-secret123456",
            },
        },
        session_id="session_worker_tool",
    )
    result = json.loads(raw)
    assert result["success"] is True

    worker_state = run.worker_state_path.read_text(encoding="utf-8")
    assert "sk-secret123456" not in worker_state
    assert "api_key=<redacted>" in worker_state
    assert '"api_key": "<redacted>"' in worker_state


def test_missing_worker_artifact_blocks_finalization(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_worker_final", workspace_path=tmp_path, run_id="run_worker_final")
    record_worker_state(
        worker_id="worker_report",
        objective="Produce worker report.",
        status="completed",
        model_lane="delegation.fast_worker",
        output_contract={"expected_artifact": "reports/worker.md"},
        parent_acceptance="accepted",
        spot_audit="No material claims; checked output contract.",
        session_id="session_worker_final",
    )

    result = write_finalization(
        objective="Accept delegated report.",
        verification="Checked worker manifest.",
        session_id="session_worker_final",
    )

    assert result["verdict"] == "blocked"
    assert "missing_worker_artifacts" in result["blockers"]
    finalization = run.finalization_path.read_text(encoding="utf-8")
    assert "Worker `worker_report` expected `reports/worker.md`" in finalization


def test_worker_material_claims_require_parent_acceptance_and_spot_audit(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_worker_claims", workspace_path=tmp_path, run_id="run_worker_claims")
    artifact = tmp_path / "reports" / "worker.md"
    artifact.parent.mkdir()
    artifact.write_text("evidence-backed report", encoding="utf-8")

    record_worker_state(
        worker_id="worker_claims",
        objective="Audit threshold claim.",
        status="completed",
        model_lane="delegation.fast_worker",
        output_contract={"expected_artifact": "reports/worker.md"},
        material_claims=["Compression threshold defaults to 0.5."],
        session_id="session_worker_claims",
    )
    result = write_finalization(
        objective="Accept delegated claims.",
        verification="Checked worker manifest.",
        session_id="session_worker_claims",
    )
    assert result["verdict"] == "blocked"
    assert "worker_parent_acceptance_missing" in result["blockers"]
    assert "worker_claim_audit_missing" in result["blockers"]

    record_worker_state(
        worker_id="worker_claims",
        objective="Audit threshold claim.",
        status="completed",
        model_lane="delegation.fast_worker",
        output_contract={"expected_artifact": "reports/worker.md"},
        material_claims=[
            {
                "statement": "Compression threshold defaults to 0.5.",
                "refs": ["config.yaml:42"],
            }
        ],
        parent_acceptance="accepted",
        spot_audit="Parent checked `config.yaml:42` against the worker claim.",
        session_id="session_worker_claims",
    )
    accepted = write_finalization(
        objective="Accept delegated claims.",
        verification="Checked worker manifest and source ref.",
        session_id="session_worker_claims",
    )
    assert accepted["verdict"] == "accepted"
