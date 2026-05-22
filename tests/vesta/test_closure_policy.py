from vesta_runtime.closure import build_closure_prompt_contract


def test_closure_contract_is_domain_neutral_and_short():
    contract = build_closure_prompt_contract()

    assert contract.startswith("Vesta closure discipline:")
    assert "research" in contract
    assert "planning" in contract
    assert "workers" in contract
    assert "code changed" in contract
    assert "run_status" in contract
    assert "ledger_append" in contract
    assert "artifact_record" in contract
    assert "research_artifact_section_write" in contract
    assert "one large write_file" in contract
    assert "finalize_run" in contract
    assert "simulate state via terminal" in contract
    assert "coding agent" not in contract.lower()
    assert len(contract.splitlines()) <= 7
