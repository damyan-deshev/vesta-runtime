# Slice 06 - Artifact Commitments And Finalization Gate

Status: ready
Mode: AFK
Blocked by: 00, 01, 02, 05

## User Value

Final answers reflect recorded state instead of confident memory. Missing
artifacts, unsupported material claims, failed verification, contradictions,
and skipped checks are visible before completion.

## Sources

- PRD: Gates And Finalization, Artifacts
- User stories: C10, C11, C12, C13, S06, S07, S08, E09, O11
- Hermes overlap: build Vesta finalization packet; use lifecycle/finalize hooks
  only where sufficient

## Hermes Surfaces To Reuse

- session/tool transcripts as evidence inputs
- lifecycle/finalization hooks where available
- raw refs and ledger state from prior slices

## Vertical Scope

Implement finalization around domain-neutral run state:

1. Track expected artifacts from user requests, model commitments, worker
   contracts, and known run paths.
2. Maintain `artifact-manifest.md`.
3. Before final answer, check objective, commitments, artifacts, material
   claims, gaps, contradictions, failures, worker state, verification/skip
   reason, and next action.
4. Use repair-first behavior for missing state.
5. Produce `finalization.md`.
6. Allow non-code finalization without tests/diffs unless the task touches code
   or risky operational behavior.

## Interfaces / Contracts

`artifact-manifest.md` entry:

```text
artifact_id:
path:
type:
expected_by:
status: expected | exists | missing | superseded | purged
verification:
impact_if_missing:
```

`finalization.md` sections:

- Objective
- Outputs
- Verification
- Material claims
- Gaps and contradictions
- Worker status
- Residual risk
- Next action
- Verdict

## Acceptance Criteria

- Missing expected artifact blocks or qualifies finalization.
- Unsupported high-materiality claim is labeled, repaired, or blocked.
- Failed command/test is visible in finalization.
- Non-code run can finish with gaps and residual risk without fake tests.
- Normal chat does not become an artifact unless there is a contract.

## Verification

Command target once implemented:

```bash
source .venv/bin/activate 2>/dev/null || source venv/bin/activate
pytest tests/vesta/test_finalization.py -q
```

Manual checks:

1. Create one expected artifact and leave it missing.
2. Try to finalize.
3. Confirm finalization blocks or qualifies output.
4. Add artifact, rerun finalization, confirm verdict updates.

Visual inspection:

- Required: inspect `artifact-manifest.md` and `finalization.md` for readable,
  non-bureaucratic output.
- Browser automation: not applicable.

## QA And Fix-Forward Gate

If finalization can declare success with missing artifacts or contradictions,
fix before worker, eval, validator, or handoff slices. This slice defines the
runtime's truth accounting.

## QA Result

Status: pass
Verification command: `uv run --extra dev pytest tests/vesta -q`
Manual checks: focused tests cover missing artifact blocking, existing artifact
with non-code skip reason, and tool-driven artifact/finalization flow.
Visual/browser checks: not applicable.
Fix-forward notes: none for this slice.
Residual risk: artifact manifest is append-only Markdown; supersede/update
semantics can be tightened when real artifact workflows appear.

## Out Of Scope

- Full validator engine.
- Enterprise audit/governance.
- UI finalization dashboard.
