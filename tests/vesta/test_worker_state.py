import json
from types import SimpleNamespace

from model_tools import handle_function_call
from vesta_runtime import (
    create_run,
    record_validator_result,
    record_worker_state,
    set_current_run,
    write_control_plane_snapshot,
    write_finalization,
)


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
    assert "Child Run ID: ``" in worker_state
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


def test_rejected_worker_blocks_finalization(tmp_path):
    set_current_run(None)
    create_run(session_id="session_worker_rejected", workspace_path=tmp_path, run_id="run_worker_rejected")

    record_worker_state(
        worker_id="worker_rejected",
        objective="Spawn delegated checker.",
        status="rejected",
        model_lane="delegation.fast_worker",
        failures=["No eligible delegate model."],
        session_id="session_worker_rejected",
    )

    result = write_finalization(
        objective="Accept delegated work.",
        verification="No worker output exists.",
        session_id="session_worker_rejected",
    )

    assert result["verdict"] == "blocked"
    assert "failed_workers" in result["blockers"]


def test_delegate_task_records_runtime_worker_boundaries(tmp_path, monkeypatch):
    set_current_run(None)
    run = create_run(session_id="session_parent_delegate", workspace_path=tmp_path, run_id="run_parent_delegate")

    class FakeChild:
        def __init__(self, task_index: int):
            self.session_id = f"session_child_{task_index}"
            self.model = "qwen3.6-35b"
            self.provider = "llama.cpp"
            self._delegate_role = "leaf"
            self._delegate_depth = 1
            self._subagent_id = f"subagent_{task_index}"
            self._parent_subagent_id = None
            self._credential_pool = None
            self.tool_progress_callback = None
            self.session_prompt_tokens = 11
            self.session_completion_tokens = 7
            self.session_reasoning_tokens = 0
            self.session_estimated_cost_usd = 0.0
            self.vesta_run = None
            self._task_index = task_index

        def get_activity_summary(self):
            return {"api_call_count": 0, "max_iterations": 1, "current_tool": None}

        def run_conversation(self, user_message: str, task_id: str):
            report = tmp_path / "reports" / "worker.md"
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text("worker report", encoding="utf-8")
            self.vesta_run = SimpleNamespace(run_id=f"run_child_{self._task_index}")
            return {
                "completed": True,
                "final_response": "Worker produced reports/worker.md",
                "api_calls": 1,
                "messages": [],
            }

        def close(self):
            pass

    def fake_build_child_agent(**kwargs):
        return FakeChild(kwargs["task_index"])

    monkeypatch.setattr("tools.delegate_tool._build_child_agent", fake_build_child_agent)

    from tools.delegate_tool import delegate_task

    parent = SimpleNamespace(
        session_id="session_parent_delegate",
        provider="llama.cpp",
        model="qwen3.6-27b",
        vesta_run=run,
        _delegate_depth=0,
        _current_task_id=None,
        _memory_manager=None,
        _interrupt_requested=False,
        session_estimated_cost_usd=0.0,
        session_cost_source="none",
        session_cost_status="unknown",
    )

    raw = delegate_task(
        goal="Produce delegated worker report.",
        worker_id="worker_delegate",
        output_contract={"expected_artifact": "reports/worker.md"},
        expected_artifact_paths=["reports/worker.md"],
        parent_agent=parent,
    )
    result = json.loads(raw)

    child_result = result["results"][0]
    assert child_result["status"] == "completed"
    assert child_result["worker_id"] == "worker_delegate"
    assert child_result["child_session_id"] == "session_child_0"
    assert child_result["child_run_id"] == "run_child_0"
    assert child_result["output_contract"] == {"expected_artifact": "reports/worker.md"}
    assert child_result["expected_artifact_paths"] == ["reports/worker.md"]
    assert child_result["observed_artifact_paths"] == ["reports/worker.md"]

    worker_state = run.worker_state_path.read_text(encoding="utf-8")
    assert "worker_delegate - requested" in worker_state
    assert "worker_delegate - accepted" in worker_state
    assert "worker_delegate - running" in worker_state
    assert "worker_delegate - completed" in worker_state
    assert "Child Session ID: `session_child_0`" in worker_state
    assert "Child Run ID: `run_child_0`" in worker_state
    assert 'Expected Artifact Paths: `["reports/worker.md"]`' in worker_state
    assert 'Structured Payload: `{"artifacts": ["reports/worker.md"]' in worker_state
    assert "Parent Acceptance: `unreviewed`" in worker_state

    record_validator_result(
        trigger="parent validator lane",
        scope="worker_delegate output",
        mode="model",
        status="passed",
        primary_result_ref="reports/worker.md",
        session_id="session_parent_delegate",
    )
    control = write_control_plane_snapshot(
        session_id="session_parent_delegate",
        next_action="Parent must accept or reject worker_delegate.",
    )
    control_plane = run.control_plane_path.read_text(encoding="utf-8")
    assert control["validator_status"] == "passed"
    assert "Validator Status: `passed`" in control_plane
    assert "parent acceptance `unreviewed`" in control_plane
    assert "child session `session_child_0`" in control_plane
