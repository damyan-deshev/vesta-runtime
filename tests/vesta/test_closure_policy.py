from vesta_runtime.closure import build_closure_prompt_contract


def test_closure_contract_is_domain_neutral_and_short():
    contract = build_closure_prompt_contract()

    assert contract.startswith("Vesta closure discipline:")
    assert "research" in contract
    assert "planning" in contract
    assert "workers" in contract
    assert "code changed" in contract
    assert "coding agent" not in contract.lower()
    assert len(contract.splitlines()) <= 6
