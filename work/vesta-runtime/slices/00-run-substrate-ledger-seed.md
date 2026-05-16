# Slice 00 - Run Substrate And Ledger Seed

Status: ready
Mode: AFK
Blocked by: none

## User Value

Starting a Vesta-enabled local run immediately leaves inspectable state on disk:
a stable `run_id`, run directory, `run.md`, `ledger.md`, and Hermes session
lineage. This is the smallest vertical foundation every later slice depends on.

## Sources

- PRD: Run Substrate, UX, Data / Integration Requirements, Testing / QA
- User stories: C01, C02, C05, C13, S02, S13, O01, O04, O05
- Hermes overlap: extend session lineage; reuse `get_hermes_home()` and
  `hermes_time.now()`

## Hermes Surfaces To Reuse

- `hermes_constants.get_hermes_home()`
- `hermes_constants.display_hermes_home()`
- `hermes_time.now()`
- Hermes `session_id`, `parent_session_id`, `task_id`
- `SessionDB` only as supporting session metadata, not as Vesta ledger

## Vertical Scope

Implement the first Vesta run lifecycle path:

1. Resolve active workspace identity and active Hermes home.
2. Create stable Vesta `run_id`.
3. Create run directory under active Hermes home.
4. Seed `run.md` and `ledger.md` before material work.
5. Record Hermes session lineage and runtime timestamp in `run.md`.
6. Keep state outside project repos by default.

This is infrastructure, but it cannot be embedded in a later slice because all
later QA needs a run directory and ledger path.

## Interfaces / Contracts

- Run path shape:

```text
{get_hermes_home()}/vesta/workspaces/<workspace_hash>/runs/<run_id>/
  run.md
  ledger.md
```

- `run.md` minimum fields:
  - `run_id`
  - workspace locator/hash
  - created timestamp from runtime
  - active Hermes `session_id`
  - parent/session lineage when known
  - prompt/cache policy summary

- `ledger.md` minimum sections:
  - Objective
  - Decisions
  - Claims
  - Actions
  - Gaps
  - Artifacts
  - Workers
  - Next Action

## Acceptance Criteria

- A new Vesta run creates the run directory before the first material action.
- `run_id` does not equal Hermes `session_id`.
- `run.md` records Hermes session id and active Hermes home.
- `ledger.md` is Markdown and human-readable.
- No Vesta state is written into the project repo unless explicitly exported.
- Timestamps are runtime-owned.

## Verification

Command target once implemented:

```bash
source .venv/bin/activate 2>/dev/null || source venv/bin/activate
pytest tests/vesta/test_run_substrate.py -q
```

Manual checks:

1. Start a minimal Vesta-enabled run.
2. Inspect the generated run directory with `find`.
3. Open `run.md` and `ledger.md`.
4. Confirm readable Markdown, stable run id, session lineage, and no project
   repo pollution.

Visual inspection:

- Required: human inspection of generated Markdown readability.
- Browser automation: not applicable.
- Failure examples: raw JSON blob in `ledger.md`, missing headings, path under
  project repo, guessed timestamps.

## QA And Fix-Forward Gate

Do not start dependent slices until the verification command and manual file
inspection pass. If file placement or timestamp ownership is wrong, fix this
slice first because downstream slices will write into the same state root.

## QA Result

Status: pass
Verification command: `uv run --extra dev pytest tests/vesta/test_run_substrate.py tests/vesta/test_ledger_append.py tests/vesta/test_raw_refs.py -q`
Manual checks: covered by file assertions for run directory, `run.md`,
`ledger.md`, raw index, and Hermes lineage.
Visual/browser checks: not applicable; Markdown readability covered by content
assertions.
Fix-forward notes: none for this slice.
Residual risk: full live compaction path is covered later by Slice 05.

## Out Of Scope

- Ledger append tool behavior.
- Raw output capture.
- Compaction/resume.
- UI/dashboard inspection.
