# Slice 07 - Worker State And Parent Acceptance

Status: completed
Mode: AFK
Blocked by: 00, 01, 02, 06

## User Value

Delegated work becomes inspectable. Parent agents accept worker output only
after worker state, artifacts, failures, gaps, and material claims are visible.

## Sources

- PRD: Workers
- User stories: C20, C21, E02, E03, E04, O06
- Hermes overlap: extend `delegate_task`, `delegation.*`, child sessions, and
  TUI spawn-tree snapshots

## Hermes Surfaces To Reuse

- `delegate_task`
- delegation model/provider/base URL config
- child `AIAgent` sessions
- existing delegation limits/truncation behavior
- TUI spawn-tree visibility as non-authoritative signal

## Vertical Scope

Wrap Hermes delegation with Vesta worker state:

1. Record requested worker objective and output contract.
2. Record accepted/spawned worker id and model/provider class without secrets.
3. Capture status: requested, accepted, running, completed, failed, truncated,
   cancelled.
4. Record artifact paths, raw refs, failures, gaps, and next action.
5. Parent acceptance requires worker state and spot audit of material claims.
6. Finalization includes worker summary and missing worker artifacts.

## Interfaces / Contracts

`worker-state.md` entry:

```text
worker_id:
parent_run_id:
child_session_id:
objective:
output_contract:
model_lane:
status:
artifacts:
failures:
gaps:
material_claims:
parent_acceptance:
```

## Acceptance Criteria

- Requested vs accepted workers are distinguishable.
- Truncated/spawn-limited workers are not counted as completed.
- Missing expected worker artifact affects finalization.
- Worker prose alone is not accepted as source truth for material claims.
- Adjacent worker model lane is explicit/config-driven.

## Verification

Command target once implemented:

```bash
source .venv/bin/activate 2>/dev/null || source venv/bin/activate
pytest tests/vesta/test_worker_state.py -q
```

Manual checks:

1. Run a fake or lightweight delegated task with expected artifact.
2. Simulate worker failure or missing artifact.
3. Confirm `worker-state.md` and `finalization.md` record the issue.
4. Confirm model/provider metadata omits secrets.

Visual inspection:

- Required: inspect worker state readability.
- Browser/TUI check: optional after Slice 11; do not depend on TUI as truth.

## QA And Fix-Forward Gate

If worker truncation or missing artifacts can appear as success, fix before
validator or end-to-end slices. Worker acceptance is a high-risk orchestration
surface.

## Out Of Scope

- Autonomous per-turn model router.
- Always-on worker spawning.
- Full multi-agent board product.

## QA Result

Status: pass
Verification command: `uv run --extra dev pytest tests/vesta -q`
Manual checks: Inspected `worker-state.md` format through tests and finalization
output paths.
Visual/browser checks: not applicable; TUI/dashboard visibility is deferred to
Slice 11.
Fix-forward notes: Added runtime write lock while implementing worker state to
reduce concurrent append risk.
Residual risk: `delegate_task` is not auto-wrapped yet; v0 exposes the durable
worker-state tool and finalization gate, with deeper delegation hook-up left to
later execution if needed.
