# Slice 10 - Selective Validator Contract

Status: completed
Mode: AFK
Blocked by: 06, 07, 08

## User Value

High-risk work can record a skeptical validation result without pretending that
Vesta already has a full always-on validator engine.

## Sources

- PRD: Validator Boundary
- User stories: S15, S16, O07, T04, T09
- Hermes overlap: build contract; later execution can reuse delegation or
  auxiliary model lanes

## Hermes Surfaces To Reuse

- delegation model lanes when validator execution is added
- deterministic command/test outputs from coding eval slice
- finalization packet

## Vertical Scope

Define and implement validator result recording:

1. Add a validator contract section to run state.
2. Support deterministic/high-risk checks where available.
3. Record primary output, tests, and validator findings separately.
4. Make finalization display validator status as absent, skipped, passed,
   failed, or inconclusive.
5. Keep always-on validator out of v0.

## Interfaces / Contracts

`validator-result.md`:

```text
trigger:
scope:
mode: deterministic | model | manual | skipped
primary_result_ref:
test_result_refs:
validator_findings:
decision_impact:
```

## Acceptance Criteria

- Validator absence is not treated as pass.
- Validator findings are not mixed into primary model score.
- Failed or inconclusive validator result affects finalization.
- The contract works even if validator execution is skipped.
- Always-on validator is not required.

## Verification

Command target once implemented:

```bash
source .venv/bin/activate 2>/dev/null || source venv/bin/activate
pytest tests/vesta/test_validator_contract.py -q
```

Manual checks:

1. Run a coding eval with validator skipped.
2. Confirm finalization says skipped, with reason.
3. Add a fake validator finding.
4. Confirm finalization separates primary/test/validator status.

Visual inspection:

- Required: inspect `validator-result.md` and `finalization.md`.
- Browser automation: not applicable.

## QA And Fix-Forward Gate

If validator status can be confused with primary success, fix before handoff and
end-to-end regression. This slice protects benchmark interpretability.

## Out Of Scope

- Full second-model validator engine.
- Always-on validator.
- Automatic trigger taxonomy beyond initial contract.

## QA Result

Status: pass
Verification command: `uv run --extra dev pytest tests/vesta -q`
Manual checks: Inspected finalization output through tests for absent, skipped,
failed, and inconclusive validator states.
Visual/browser checks: not applicable.
Fix-forward notes: Kept validator recording as a contract surface only; no
always-on validator engine added.
Residual risk: Future validator execution still needs model-lane/delegation
wiring; v0 records and gates the result once available.
