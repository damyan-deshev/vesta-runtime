# Slice 05 - Ledger-Aware Compaction And Resume Packet

Status: ready
Mode: AFK
Blocked by: 00, 01, 02

## User Value

Compaction no longer turns active work into a fragile prose summary. Vesta
checkpoints operational state and resumes with objective, commitments, gaps,
artifacts, workers, and exactly one next action.

## Sources

- PRD: Compaction / Resume
- User stories: C09, S20, E01, E07
- Hermes overlap: extend compression-linked child sessions and resume tip
  resolution

## Hermes Surfaces To Reuse

- Hermes compaction child session behavior
- `parent_session_id` lineage
- resume session resolution
- existing compressor output only as input, not as authoritative state

## Vertical Scope

Implement Vesta compaction hook behavior:

1. Before compaction, append a checkpoint entry to `ledger.md`.
2. Build `resume-packet.md` from active ledger/run state.
3. Record Hermes parent and child session ids.
4. If work remains, set exactly one non-empty next action.
5. After resume, force the first material action to consult ledger/resume
   packet before rereading source.
6. Avoid ceremony when no material state exists.

## Interfaces / Contracts

`resume-packet.md` must include:

- objective
- current phase
- active commitments
- active decisions
- verified claims
- open gaps
- contradictions
- worker status
- artifact manifest summary
- ledger path
- next action
- Hermes session lineage

## Acceptance Criteria

- Compaction writes a checkpoint ledger entry.
- Resume packet is generated from ledger/run state, not only transcript prose.
- Unfinished deliverable means `next_action` is not `None`.
- Child session lineage is visible from run state.
- Post-compact rereads are suppressed unless needed for verification.

## Verification

Command target once implemented:

```bash
source .venv/bin/activate 2>/dev/null || source venv/bin/activate
pytest tests/vesta/test_compaction_resume.py -q
```

Manual checks:

1. Create a run with an unfinished artifact commitment.
2. Trigger or simulate compaction.
3. Inspect `ledger.md` and `resume-packet.md`.
4. Resume and confirm next action points to unfinished work.

Visual inspection:

- Required: inspect `resume-packet.md` for compact readability.
- Browser automation: optional later through TUI/dashboard.

## QA And Fix-Forward Gate

If resume loses objective, deliverable pressure, or next action, stop and fix
before finalization, workers, or end-to-end slices. This is the key long-run
survival contract.

## QA Result

Status: pass
Verification command: `uv run --extra dev pytest tests/vesta -q`
Manual checks: focused tests cover explicit resume packet generation and
session-rotation checkpoint behavior.
Visual/browser checks: not applicable.
Fix-forward notes: none for this slice.
Residual risk: live LLM compression quality remains Hermes-owned; Vesta now
records durable resume state around the rotation.

## Out Of Scope

- Rewriting Hermes compressor.
- Changing Hermes session storage model.
- Full UI resume inspector.
