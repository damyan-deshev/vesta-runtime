import json

from model_tools import handle_function_call
from vesta_runtime import (
    create_run,
    record_validator_result,
    set_current_run,
    write_finalization,
)


def test_validator_absence_is_displayed_not_treated_as_pass(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_validator_absent", workspace_path=tmp_path, run_id="run_validator_absent")

    result = write_finalization(
        objective="Finalize low-risk work.",
        verification="Tests passed.",
        session_id="session_validator_absent",
    )

    assert result["verdict"] == "accepted"
    finalization = run.finalization_path.read_text(encoding="utf-8")
    assert "Validator Status: `absent`" in finalization
    assert "Validator Status: `passed`" not in finalization


def test_validator_skipped_with_reason_does_not_block(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_validator_skipped", workspace_path=tmp_path, run_id="run_validator_skipped")
    record_validator_result(
        trigger="low-risk docs-only change",
        scope="README edit",
        mode="skipped",
        status="skipped",
        skip_reason="No material runtime behavior changed.",
        session_id="session_validator_skipped",
    )

    result = write_finalization(
        objective="Finalize docs-only work.",
        verification="Manual inspection completed.",
        session_id="session_validator_skipped",
    )

    assert result["verdict"] == "accepted"
    finalization = run.finalization_path.read_text(encoding="utf-8")
    assert "Validator Status: `skipped`" in finalization
    assert "No material runtime behavior changed." in finalization


def test_failed_or_inconclusive_validator_blocks_finalization(tmp_path):
    set_current_run(None)
    run = create_run(session_id="session_validator_failed", workspace_path=tmp_path, run_id="run_validator_failed")
    record_validator_result(
        trigger="high-risk eval",
        scope="coding eval verdict",
        mode="manual",
        status="failed",
        primary_result_ref="raw/eval_primary.txt",
        test_result_refs=["raw/eval_tests.txt"],
        validator_findings=["Diff does not support the claimed fix."],
        decision_impact="Do not accept final report.",
        session_id="session_validator_failed",
    )

    result = write_finalization(
        objective="Finalize high-risk eval.",
        verification="Primary tests passed.",
        session_id="session_validator_failed",
    )

    assert result["verdict"] == "blocked"
    assert "validator_failed" in result["blockers"]
    finalization = run.finalization_path.read_text(encoding="utf-8")
    assert "Diff does not support the claimed fix." in finalization
    assert "Primary Result Ref: `raw/eval_primary.txt`" in finalization


def test_validator_record_tool_updates_active_run(tmp_path, monkeypatch):
    set_current_run(None)
    run = create_run(session_id="session_validator_tool", workspace_path=tmp_path, run_id="run_validator_tool")
    monkeypatch.setenv("HERMES_SESSION_ID", "session_validator_tool")

    raw = handle_function_call(
        "validator_result_record",
        {
            "trigger": "manual audit",
            "scope": "worker report",
            "mode": "manual",
            "status": "inconclusive",
            "validator_findings": ["Need one more source range."],
            "decision_impact": "Hold finalization.",
        },
        session_id="session_validator_tool",
    )
    result = json.loads(raw)

    assert result["success"] is True
    assert result["status"] == "inconclusive"
    validator_result = run.validator_result_path.read_text(encoding="utf-8")
    assert "Need one more source range." in validator_result
