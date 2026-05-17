import json

from run_agent import AIAgent
from vesta_runtime import (
    append_ledger_entry,
    create_run,
    enforce_eval_contract,
    record_artifact,
    seed_eval_contract_from_prompt,
    set_current_run,
    validate_delegate_task_against_eval_contract,
    write_finalization,
    write_research_artifact_section,
)


def _tool_call(name: str, args: dict) -> dict:
    return {
        "role": "assistant",
        "tool_calls": [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(args),
                },
            }
        ],
    }


def test_eval_contract_seeds_expected_artifact_from_prompt(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_SOURCE", "eval")
    set_current_run(None)
    run = create_run(session_id="session_eval_contract", workspace_path=tmp_path, run_id="run_eval_contract")
    artifact = tmp_path / "live-eval-artifacts" / "report.md"
    prompt = (
        "Hard contract: call artifact_record and finalize_run.\n"
        f"Write artifact: {artifact}\n"
    )

    result = seed_eval_contract_from_prompt(prompt=prompt, session_id="session_eval_contract")

    assert result["seeded"] is True
    assert result["expected_artifact"] == str(artifact)
    assert (run.run_dir / "eval-contract.md").exists()
    manifest = run.artifact_manifest_path.read_text(encoding="utf-8")
    assert "Expected By: `eval_contract`" in manifest
    assert "Status: `expected`" in manifest


def test_eval_contract_seeds_and_validates_required_delegate_contract(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_SOURCE", "eval")
    set_current_run(None)
    run = create_run(
        session_id="session_eval_delegate_required",
        workspace_path=tmp_path,
        run_id="run_eval_delegate_required",
    )
    artifact = tmp_path / "live-eval-artifacts" / "report.md"
    validator_artifact = tmp_path / "live-eval-artifacts" / "validator.md"
    prompt = (
        "Hard contract: call artifact_record, delegate_task, and finalize_run.\n"
        f"Parent artifact: {artifact}\n"
        "`worker_id`: `sensenova-u1-validator`\n"
        f"Validator artifact: {validator_artifact}\n"
    )

    seed = seed_eval_contract_from_prompt(
        prompt=prompt,
        session_id="session_eval_delegate_required",
    )

    contract_text = (run.run_dir / "eval-contract.md").read_text(encoding="utf-8")
    assert seed["required_delegate_worker_id"] == "sensenova-u1-validator"
    assert seed["required_delegate_artifact"] == str(validator_artifact)
    assert "- Required Delegate Worker ID: `sensenova-u1-validator`" in contract_text
    assert f"- Required Delegate Artifact: `{validator_artifact}`" in contract_text

    wrong = validate_delegate_task_against_eval_contract(
        {
            "tasks": [
                {
                    "goal": "Validate report.",
                    "worker_id": "worker_auto",
                    "output_contract": {"expected_artifact": str(validator_artifact)},
                    "expected_artifact_paths": [str(validator_artifact)],
                }
            ]
        }
    )
    assert wrong
    assert "sensenova-u1-validator" in wrong[0]

    missing_artifact = validate_delegate_task_against_eval_contract(
        {
            "tasks": [
                {
                    "goal": "Validate report.",
                    "worker_id": "sensenova-u1-validator",
                    "output_contract": {"required_sections": ["verdict"]},
                }
            ]
        }
    )
    assert missing_artifact
    assert "Required delegate artifact" in missing_artifact[0] or "requires delegate artifact" in missing_artifact[0]

    correct = validate_delegate_task_against_eval_contract(
        {
            "tasks": [
                {
                    "goal": "Validate report.",
                    "worker_id": "sensenova-u1-validator",
                    "output_contract": {"expected_artifact": str(validator_artifact)},
                    "expected_artifact_paths": [str(validator_artifact)],
                }
            ]
        }
    )
    assert correct == []


def test_eval_contract_seeds_natural_research_prompt_with_delegate_contract(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_SOURCE", "eval")
    set_current_run(None)
    run = create_run(
        session_id="session_eval_natural_research",
        workspace_path=tmp_path,
        run_id="run_eval_natural_research",
    )
    artifact = tmp_path / "live-eval-artifacts" / "sensenova-parent.md"
    validator_artifact = tmp_path / "live-eval-artifacts" / "sensenova-validator.md"
    prompt = f"""
# SenseNova-U1 Research Eval

You are running under Vesta eval mode. This is a research workflow test, not a coding task.

Expected parent research artifact:

`{artifact}`

Expected validator artifact:

`{validator_artifact}`

Operating requirements:

5. Use `delegate_task` at least once for an independent validator lane.
   - Use `worker_id`: `sensenova-u1-validator`.
   - Use an `output_contract` object containing:
     - `expected_artifact`: `{validator_artifact}`
   - Use `expected_artifact_paths` containing the validator artifact path.
10. Finalize the run.
11. Write a control-plane snapshot.
"""

    seed = seed_eval_contract_from_prompt(
        prompt=prompt,
        session_id="session_eval_natural_research",
    )

    contract_text = (run.run_dir / "eval-contract.md").read_text(encoding="utf-8")
    assert seed["seeded"] is True
    assert seed["expected_artifact"] == str(artifact)
    assert seed["contract_profile"] == "research_ledger"
    assert seed["required_delegate_worker_id"] == "sensenova-u1-validator"
    assert seed["required_delegate_artifact"] == str(validator_artifact)
    assert f"- Expected Artifact: `{artifact}`" in contract_text
    assert "- Required Delegate Worker ID: `sensenova-u1-validator`" in contract_text
    assert f"- Required Delegate Artifact: `{validator_artifact}`" in contract_text


def test_eval_contract_blocks_terminal_simulated_vesta_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_SOURCE", "eval")
    set_current_run(None)
    run = create_run(session_id="session_eval_contract", workspace_path=tmp_path, run_id="run_eval_contract_block")
    artifact = tmp_path / "live-eval-artifacts" / "report.md"
    seed_eval_contract_from_prompt(
        prompt=f"artifact_record finalize_run {artifact}",
        session_id="session_eval_contract",
    )
    messages = [
        _tool_call("write_file", {"path": str(artifact), "content": "report"}),
        _tool_call(
            "terminal",
            {
                "command": (
                    "python -c \"print({'verdict':'PASS','artifact_id':'report.md',"
                    "'ledger_updated': True})\""
                )
            },
        ),
    ]

    result = enforce_eval_contract(
        messages=messages,
        final_response="PASS - artifact verified and finalization verdict accepted.",
        objective="Run eval.",
        session_id="session_eval_contract",
    )

    assert result["checked"] is True
    assert result["compliant"] is False
    assert result["verdict"] == "blocked"
    assert "artifact_record:expected" in result["missing_order"]
    assert result["terminal_simulations"] == ["terminal"]
    finalization = run.finalization_path.read_text(encoding="utf-8")
    assert "Eval contract required typed tool order is incomplete" in finalization
    assert "simulate Vesta state" in finalization
    assert "Finalization Status: `blocked`" in run.control_plane_path.read_text(encoding="utf-8")


def test_eval_contract_blocks_execute_code_simulated_vesta_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_SOURCE", "eval")
    set_current_run(None)
    run = create_run(
        session_id="session_eval_contract",
        workspace_path=tmp_path,
        run_id="run_eval_contract_execute_code_block",
    )
    artifact = tmp_path / "live-eval-artifacts" / "report.md"
    seed_eval_contract_from_prompt(
        prompt=f"artifact_record finalize_run {artifact}",
        session_id="session_eval_contract",
    )
    messages = [
        _tool_call("write_file", {"path": str(artifact), "content": "report"}),
        _tool_call(
            "execute_code",
            {
                "code": (
                    "print({'verdict':'PASS','artifact_id':'report.md',"
                    "'ledger_updated': True})"
                )
            },
        ),
    ]

    result = enforce_eval_contract(
        messages=messages,
        final_response="PASS - artifact verified and finalization verdict accepted.",
        objective="Run eval.",
        session_id="session_eval_contract",
    )

    assert result["checked"] is True
    assert result["compliant"] is False
    assert result["verdict"] == "blocked"
    assert result["terminal_simulations"] == ["execute_code"]
    finalization = run.finalization_path.read_text(encoding="utf-8")
    assert "simulate Vesta state" in finalization
    assert "Finalization Status: `blocked`" in run.control_plane_path.read_text(encoding="utf-8")


def test_eval_contract_accepts_typed_tool_order_and_vesta_state(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_SOURCE", "eval")
    set_current_run(None)
    run = create_run(session_id="session_eval_contract", workspace_path=tmp_path, run_id="run_eval_contract_ok")
    artifact = tmp_path / "live-eval-artifacts" / "report.md"
    seed_eval_contract_from_prompt(
        prompt=f"artifact_record finalize_run {artifact}",
        session_id="session_eval_contract",
    )
    artifact.parent.mkdir()
    artifact.write_text("report", encoding="utf-8")
    record_artifact(
        path=str(artifact),
        artifact_type="eval_artifact",
        expected_by="model_contract",
        status="exists",
        session_id="session_eval_contract",
    )
    append_ledger_entry(
        entry_type="claim",
        title="Eval artifact written",
        statement="Eval artifact exists.",
        status="verified",
        materiality="high",
        refs=[str(artifact)],
        session_id="session_eval_contract",
    )
    write_finalization(
        objective="Run eval.",
        skip_reason="Non-code eval artifact.",
        session_id="session_eval_contract",
    )
    messages = [
        _tool_call("artifact_record", {"path": str(artifact), "status": "expected"}),
        _tool_call("write_file", {"path": str(artifact), "content": "report"}),
        _tool_call("artifact_record", {"path": str(artifact), "status": "exists"}),
        _tool_call("ledger_append", {"entry_type": "claim"}),
        _tool_call("finalize_run", {"objective": "Run eval.", "skip_reason": "Non-code eval artifact."}),
    ]

    result = enforce_eval_contract(
        messages=messages,
        final_response=f"Artifact: {artifact}\nFinalization verdict: accepted",
        objective="Run eval.",
        session_id="session_eval_contract",
    )

    assert result["checked"] is True
    assert result["compliant"] is True
    assert result["finalization_status"] == "accepted"


def test_research_ledger_contract_allows_ledger_before_artifact_write(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_SOURCE", "eval")
    set_current_run(None)
    run = create_run(session_id="session_eval_research", workspace_path=tmp_path, run_id="run_eval_research")
    artifact = tmp_path / "live-eval-artifacts" / "research.md"
    seed = seed_eval_contract_from_prompt(
        prompt=f"research workflow with evidence ledger artifact_record ledger_append finalize_run {artifact}",
        session_id="session_eval_research",
    )
    append_ledger_entry(
        entry_type="claim",
        title="Material research claim",
        statement="The product uses a ledger-first runtime state.",
        refs=["docs/VESTA_LEDGER_DESIGN.md:1"],
        status="supported",
        materiality="high",
        session_id="session_eval_research",
    )
    artifact.parent.mkdir()
    artifact.write_text("research report", encoding="utf-8")
    record_artifact(
        path=str(artifact),
        artifact_type="eval_artifact",
        expected_by="model_contract",
        status="exists",
        session_id="session_eval_research",
    )
    write_finalization(
        objective="Run research eval.",
        verification="Report exists and ledger has material claims.",
        session_id="session_eval_research",
    )
    messages = [
        _tool_call("artifact_record", {"path": str(artifact), "status": "expected"}),
        _tool_call("ledger_append", {"entry_type": "claim", "materiality": "high"}),
        _tool_call("write_file", {"path": str(artifact), "content": "research report"}),
        _tool_call("artifact_record", {"path": str(artifact), "status": "exists"}),
        _tool_call("finalize_run", {"objective": "Run research eval.", "verification": "Report exists."}),
    ]

    result = enforce_eval_contract(
        messages=messages,
        final_response=f"Finalization verdict: accepted; report path: {artifact}",
        objective="Run research eval.",
        session_id="session_eval_research",
    )

    assert seed["contract_profile"] == "research_ledger"
    assert result["checked"] is True
    assert result["compliant"] is True
    assert result["contract_profile"] == "research_ledger"
    assert "Verdict: `accepted`" in run.finalization_path.read_text(encoding="utf-8")


def test_evidence_workflow_contract_accepts_section_writer_without_artifact_record_ceremony(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_SOURCE", "eval")
    set_current_run(None)
    run = create_run(
        session_id="session_eval_evidence_workflow",
        workspace_path=tmp_path,
        run_id="run_eval_evidence_workflow",
    )
    artifact = tmp_path / "live-eval-artifacts" / "evidence.md"
    seed = seed_eval_contract_from_prompt(
        prompt=(
            "Vesta eval mode current-world evidence workflow. "
            f"Expected parent artifact: {artifact}. "
            "Success criteria: finalize the run and write a control-plane snapshot."
        ),
        session_id="session_eval_evidence_workflow",
    )
    write_research_artifact_section(
        path=str(artifact),
        section="sources",
        content="- Source: official page; Signal: direct current evidence.",
        session_id="session_eval_evidence_workflow",
    )
    append_ledger_entry(
        entry_type="verification",
        title="Evidence artifact checked",
        statement="The evidence artifact was written through the typed section writer.",
        refs=[str(artifact)],
        status="supported",
        materiality="high",
        session_id="session_eval_evidence_workflow",
    )
    write_finalization(
        objective="Run evidence workflow eval.",
        verification="Typed section writer produced the artifact and ledger recorded verification.",
        session_id="session_eval_evidence_workflow",
    )
    messages = [
        _tool_call(
            "research_artifact_section_write",
            {"path": str(artifact), "section": "sources", "content": "official source"},
        ),
        _tool_call("ledger_append", {"entry_type": "verification", "materiality": "high"}),
        _tool_call("finalize_run", {"objective": "Run evidence workflow eval."}),
        _tool_call("artifact_record", {"path": str(artifact), "status": "exists"}),
    ]

    result = enforce_eval_contract(
        messages=messages,
        final_response=f"Finalization verdict: accepted; report path: {artifact}",
        objective="Run evidence workflow eval.",
        session_id="session_eval_evidence_workflow",
    )

    assert seed["contract_profile"] == "research_ledger"
    assert seed["required_delegate_worker_id"] == ""
    assert result["checked"] is True
    assert result["compliant"] is True
    assert result["contract_profile"] == "research_ledger"
    assert "Expected By: `eval_contract`" in run.artifact_manifest_path.read_text(encoding="utf-8")
    assert "Expected By: `research_artifact_section_write`" in run.artifact_manifest_path.read_text(encoding="utf-8")


def test_eval_contract_blocks_forbidden_override_args(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_SOURCE", "eval")
    monkeypatch.setenv("VESTA_EVAL_FORBIDDEN_TOOL_ARGS", "read_file.complete_coverage,broad_read_reason")
    set_current_run(None)
    run = create_run(session_id="session_eval_forbidden", workspace_path=tmp_path, run_id="run_eval_forbidden")
    artifact = tmp_path / "live-eval-artifacts" / "report.md"
    seed_eval_contract_from_prompt(
        prompt=f"artifact_record ledger_append finalize_run {artifact}",
        session_id="session_eval_forbidden",
    )
    artifact.parent.mkdir()
    artifact.write_text("report", encoding="utf-8")
    record_artifact(
        path=str(artifact),
        artifact_type="eval_artifact",
        expected_by="model_contract",
        status="exists",
        session_id="session_eval_forbidden",
    )
    append_ledger_entry(
        entry_type="verification",
        title="Artifact verified",
        statement="Artifact exists.",
        status="accepted",
        materiality="medium",
        session_id="session_eval_forbidden",
    )
    write_finalization(
        objective="Run eval.",
        verification="Artifact exists.",
        session_id="session_eval_forbidden",
    )
    messages = [
        _tool_call("artifact_record", {"path": str(artifact), "status": "expected"}),
        _tool_call("write_file", {"path": str(artifact), "content": "report"}),
        _tool_call("read_file", {"path": "fixture.py", "complete_coverage": True}),
        _tool_call("artifact_record", {"path": str(artifact), "status": "exists"}),
        _tool_call("ledger_append", {"entry_type": "verification"}),
        _tool_call("finalize_run", {"objective": "Run eval.", "verification": "Artifact exists."}),
    ]

    result = enforce_eval_contract(
        messages=messages,
        final_response=f"Finalization verdict: accepted; report path: {artifact}",
        objective="Run eval.",
        session_id="session_eval_forbidden",
    )

    assert result["compliant"] is False
    assert result["forbidden_tool_args"] == ["read_file.complete_coverage"]
    assert result["verdict"] == "blocked"
    assert "forbidden tool arguments" in run.finalization_path.read_text(encoding="utf-8")


def test_eval_contract_blocks_empty_delegate_output_contract_for_worker_contract(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_SOURCE", "eval")
    set_current_run(None)
    run = create_run(
        session_id="session_eval_delegate_contract",
        workspace_path=tmp_path,
        run_id="run_eval_delegate_contract",
    )
    artifact = tmp_path / "live-eval-artifacts" / "report.md"
    validator_artifact = tmp_path / "live-eval-artifacts" / "validator.md"
    seed_eval_contract_from_prompt(
        prompt=f"artifact_record ledger_append finalize_run {artifact}",
        session_id="session_eval_delegate_contract",
    )
    artifact.parent.mkdir()
    artifact.write_text("report", encoding="utf-8")
    validator_artifact.write_text("validator", encoding="utf-8")
    record_artifact(
        path=str(artifact),
        artifact_type="eval_artifact",
        expected_by="model_contract",
        status="exists",
        session_id="session_eval_delegate_contract",
    )
    append_ledger_entry(
        entry_type="verification",
        title="Artifact verified",
        statement="Artifact exists.",
        status="accepted",
        materiality="medium",
        session_id="session_eval_delegate_contract",
    )
    write_finalization(
        objective="Run eval.",
        verification="Artifact exists.",
        session_id="session_eval_delegate_contract",
    )
    messages = [
        _tool_call("artifact_record", {"path": str(artifact), "status": "expected"}),
        _tool_call(
            "delegate_task",
            {
                "goal": "Validate report.",
                "worker_id": "s8-runtime-validator",
                "expected_artifact_paths": [str(validator_artifact)],
                "output_contract": {},
            },
        ),
        _tool_call("write_file", {"path": str(artifact), "content": "report"}),
        _tool_call("artifact_record", {"path": str(artifact), "status": "exists"}),
        _tool_call("ledger_append", {"entry_type": "verification"}),
        _tool_call("finalize_run", {"objective": "Run eval.", "verification": "Artifact exists."}),
    ]

    result = enforce_eval_contract(
        messages=messages,
        final_response=f"Finalization verdict: accepted; report path: {artifact}",
        objective="Run eval.",
        session_id="session_eval_delegate_contract",
    )

    assert result["compliant"] is False
    assert result["verdict"] == "blocked"
    assert result["delegate_contract_failures"]
    assert "s8-runtime-validator" in result["delegate_contract_failures"][0]
    assert "empty or incomplete output_contract" in run.finalization_path.read_text(encoding="utf-8")


def test_eval_contract_accepts_delegate_output_contract_with_expected_key(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_SOURCE", "eval")
    set_current_run(None)
    run = create_run(
        session_id="session_eval_delegate_contract_ok",
        workspace_path=tmp_path,
        run_id="run_eval_delegate_contract_ok",
    )
    artifact = tmp_path / "live-eval-artifacts" / "report.md"
    validator_artifact = tmp_path / "live-eval-artifacts" / "validator.md"
    seed_eval_contract_from_prompt(
        prompt=f"artifact_record ledger_append finalize_run {artifact}",
        session_id="session_eval_delegate_contract_ok",
    )
    artifact.parent.mkdir()
    artifact.write_text("report", encoding="utf-8")
    validator_artifact.write_text("validator", encoding="utf-8")
    record_artifact(
        path=str(artifact),
        artifact_type="eval_artifact",
        expected_by="model_contract",
        status="exists",
        session_id="session_eval_delegate_contract_ok",
    )
    append_ledger_entry(
        entry_type="verification",
        title="Artifact verified",
        statement="Artifact exists.",
        status="accepted",
        materiality="medium",
        session_id="session_eval_delegate_contract_ok",
    )
    write_finalization(
        objective="Run eval.",
        verification="Artifact exists.",
        session_id="session_eval_delegate_contract_ok",
    )
    messages = [
        _tool_call("artifact_record", {"path": str(artifact), "status": "expected"}),
        _tool_call(
            "delegate_task",
            {
                "goal": "Validate report.",
                "worker_id": "s8-runtime-validator",
                "expected_artifact_paths": [str(validator_artifact)],
                "output_contract": {"expected_artifact": str(validator_artifact)},
            },
        ),
        _tool_call("write_file", {"path": str(artifact), "content": "report"}),
        _tool_call("artifact_record", {"path": str(artifact), "status": "exists"}),
        _tool_call("ledger_append", {"entry_type": "verification"}),
        _tool_call("finalize_run", {"objective": "Run eval.", "verification": "Artifact exists."}),
    ]

    result = enforce_eval_contract(
        messages=messages,
        final_response=f"Finalization verdict: accepted; report path: {artifact}",
        objective="Run eval.",
        session_id="session_eval_delegate_contract_ok",
    )

    assert result["compliant"] is True
    assert result["finalization_status"] == "accepted"


def test_refusal_mentioning_pass_is_not_success_claim(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_SESSION_SOURCE", "eval")
    set_current_run(None)
    run = create_run(session_id="session_eval_refusal", workspace_path=tmp_path, run_id="run_eval_refusal")
    artifact = tmp_path / "live-eval-artifacts" / "report.md"
    seed_eval_contract_from_prompt(
        prompt=f"artifact_record ledger_append finalize_run {artifact}",
        session_id="session_eval_refusal",
    )

    result = enforce_eval_contract(
        messages=[],
        final_response="I refuse to claim PASS because the contract was not satisfied.",
        objective="Run eval.",
        session_id="session_eval_refusal",
    )

    assert result["compliant"] is False
    assert not any("Final response claimed success" in failure for failure in result["failures"])
    assert "Final response claimed success" not in run.finalization_path.read_text(encoding="utf-8")


def test_quiet_and_eval_source_disable_background_review(monkeypatch):
    quiet_agent = AIAgent(
        model="test/model",
        provider="test",
        api_key="test",
        base_url="http://localhost:9/v1",
        quiet_mode=True,
        skip_memory=True,
        enabled_toolsets=[],
    )
    assert quiet_agent._background_review_allowed() is False

    monkeypatch.setenv("HERMES_SESSION_SOURCE", "eval")
    eval_agent = AIAgent(
        model="test/model",
        provider="test",
        api_key="test",
        base_url="http://localhost:9/v1",
        quiet_mode=False,
        skip_memory=True,
        enabled_toolsets=[],
    )
    assert eval_agent._background_review_allowed() is False

    monkeypatch.setenv("VESTA_EVAL_BACKGROUND_REVIEW", "1")
    assert eval_agent._background_review_allowed() is True
