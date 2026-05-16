# Slice 12 - Handoff And End-To-End Regression Pack

Status: completed
Mode: AFK
Blocked by: 00-11

## User Value

A completed Vesta run can hand off its objective, decisions, evidence, gaps,
artifacts, failures, and next action to a future agent without reopening the
entire transcript.

## Sources

- PRD: Definition Of Done, Testing / QA Decisions
- User stories: O12 plus all core stories C01-C21
- Hermes overlap: reuse session/export material where useful; Vesta handoff is
  ledger-derived

## Hermes Surfaces To Reuse

- session export/search as supporting context
- run artifacts from all prior slices
- profile-aware paths

## Vertical Scope

Implement a final handoff and regression pack:

1. Generate `handoff.md` from run state.
2. Include decisions, active constraints, objective, artifacts, raw refs, worker
   state, finalization verdict, residual risk, and next action.
3. Exclude secrets and unnecessary raw payloads.
4. Provide one regression command that exercises the critical v0 path.
5. Provide manual inspection checklist.

## Interfaces / Contracts

`handoff.md` sections:

- Current objective
- Product/runtime decisions
- Completed work
- Verified claims
- Open gaps
- Artifacts
- Worker state
- Verification/finalization
- Next action
- Paths to run state

Regression path:

```text
start run -> ledger append -> raw ref -> retrieval gate -> compaction packet
-> artifact commitment -> finalization -> handoff
```

## Acceptance Criteria

- Handoff is generated from Vesta files, not transcript memory.
- Handoff names unresolved gaps and residual risk.
- Handoff includes exactly one next action when work remains.
- Regression pack covers run creation, ledger append, raw ref, retrieval policy,
  compaction/resume, artifact/finalization, and handoff.
- Human can continue from handoff without rereading all prior context.

## Verification

Command target once implemented:

```bash
source .venv/bin/activate 2>/dev/null || source venv/bin/activate
pytest tests/vesta/test_end_to_end_regression.py -q
```

Manual checks:

1. Run the regression fixture.
2. Inspect `handoff.md`.
3. Confirm all referenced paths exist or are clearly marked missing/purged.
4. Confirm next action matches latest user direction.

Visual inspection:

- Required: inspect handoff readability and absence of raw context walls.
- Browser automation: optional only if handoff is exposed through a UI.

## QA And Fix-Forward Gate

If the end-to-end path passes while an upstream contract is broken, fix the
regression pack and the failing slice. This is the release-readiness guard, not
a substitute for per-slice QA.

## Out Of Scope

- Enterprise handoff governance.
- Cloud export.
- Full documentation site.

## QA Result

Status: pass
Verification command: `uv run --extra dev pytest tests/vesta -q`
Manual checks: Regression tests inspect `handoff.md` for objective, decisions,
claims, raw refs, finalization status, exactly one top-level next action, and
run-state paths.
Visual/browser checks: not applicable; handoff is local Markdown.
Fix-forward notes: Removed duplicate top-level next-action ambiguity caused by
embedded finalization excerpts. Focused smoke also found leaked Vesta state into
legacy tests; fixed by scoping Vesta behavior to active session/workspace.
Residual risk: Full repository test suite was not run; focused integration
smoke passed for touched Hermes surfaces.
