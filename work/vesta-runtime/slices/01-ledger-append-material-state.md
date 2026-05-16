# Slice 01 - Ledger Append Primitive And Material State

Status: ready
Mode: AFK
Blocked by: 00

## User Value

The model can record material state without patching or rewriting the full
ledger. Important claims, decisions, gaps, artifacts, failures, worker updates,
and next actions survive before compaction.

## Sources

- PRD: Ledger, Gates And Finalization
- User stories: C03, C04, C06, C07, C10, C11, S04, S05, S06, S19, S20
- Hermes overlap: build ledger surface; register through Hermes tool/plugin
  surfaces where possible

## Hermes Surfaces To Reuse

- Tool registration/plugin mechanism
- Existing tool call metadata such as `task_id`, `session_id`, and
  `tool_call_id`
- `hermes_time.now()` for timestamps

## Vertical Scope

Implement `ledger_append` as the normal model-facing write path:

1. Accept small model-authored fields only.
2. Runtime adds id, timestamp, actor, run id, session id, and task id.
3. Append a Markdown entry to `ledger.md`.
4. Preserve append-only behavior for normal writes.
5. Support entry types required by v0 finalization.
6. Return a compact confirmation with entry id and ledger path.

## Interfaces / Contracts

Input fields:

- `entry_type`
- `title`
- `statement`
- `refs`
- `status`
- `materiality`
- `next_action`

Runtime-owned fields:

- `entry_id`
- timestamp
- `run_id`
- Hermes `session_id`
- `task_id`
- actor

Entry types:

- claim
- decision
- action
- gap
- contradiction
- commitment
- artifact
- worker_state
- checkpoint
- next_step
- failure

## Acceptance Criteria

- `ledger_append` cannot overwrite existing ledger content.
- Model cannot set timestamp or entry id.
- Entry format is easy for a model and human to reread.
- Material entries can cite raw/source/artifact refs when available.
- A failed or malformed append returns a repairable error.

## Verification

Command target once implemented:

```bash
source .venv/bin/activate 2>/dev/null || source venv/bin/activate
pytest tests/vesta/test_ledger_append.py -q
```

Manual checks:

1. Append one decision, one claim, one gap, one artifact, and one next step.
2. Confirm all appear in chronological order.
3. Confirm runtime fields are present and model-owned fields remain small.
4. Confirm ledger remains readable Markdown.

Visual inspection:

- Required: inspect `ledger.md` for scannable headings and no large raw payloads.
- Browser automation: not applicable.

## QA And Fix-Forward Gate

If append order, runtime-owned timestamps, or Markdown readability fail, fix
before slices that depend on ledger refs or finalization. Record failures in the
slice QA result and rerun the ledger test.

## QA Result

Status: pass
Verification command: `uv run --extra dev pytest tests/vesta/test_run_substrate.py tests/vesta/test_ledger_append.py tests/vesta/test_raw_refs.py -q`
Manual checks: ledger entries asserted for type, materiality, run id, Hermes
session id, refs, and next action.
Visual/browser checks: not applicable.
Fix-forward notes: none for this slice.
Residual risk: model behavior around when to call `ledger_append` is enforced
by prompt/tool contract now and retrieval/finalization gates later.

## Out Of Scope

- Automatic semantic classification of important outputs.
- Whole-ledger rewrite or SQL-first ledger storage.
- Compaction packet generation.
