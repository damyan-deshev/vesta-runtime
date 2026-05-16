# Slice 02 - Run-Scoped Raw Evidence Refs

Status: ready
Mode: AFK
Blocked by: 00, 01

## User Value

Large tool outputs and source reads remain inspectable without being shoved
back into prompt context or copied into the ledger.

## Sources

- PRD: Raw Capture, Raw Retention And Privacy
- User stories: C08, S03, S12, S19, E11, O03
- Hermes overlap: extend `tools/tool_result_storage.py`, `BudgetConfig`,
  terminal output transforms, and redaction primitives

## Hermes Surfaces To Reuse

- `maybe_persist_tool_result`
- `BudgetConfig`
- existing tool output caps
- terminal output transform hooks
- secret redaction helpers

## Vertical Scope

Route persisted tool/source outputs into the active Vesta run:

1. Detect output that should be persisted outside context.
2. Store full payload under `raw/`.
3. Return excerpt plus stable raw ref to the model.
4. Allow `ledger_append` to cite the raw ref.
5. Record hash, locator, capture timestamp, tool name, and status where
   available.
6. Preserve local retention by default.

## Interfaces / Contracts

Raw ref shape in Markdown:

```text
raw_ref: raw/tool_0007.txt
source: terminal | read_file | search_files | worker | other
hash: sha256:...
excerpt: ...
captured_at: ...
```

Required storage:

```text
<run_dir>/raw/
<run_dir>/raw/index.md
```

## Acceptance Criteria

- Large output is not fully inlined into `ledger.md`.
- Raw payload exists under the active run.
- Model-facing result includes a compact excerpt and path/ref.
- Raw refs can be cited by ledger entries.
- Secrets are not reintroduced into model-facing excerpts when redaction is
  configured.

## Verification

Command target once implemented:

```bash
source .venv/bin/activate 2>/dev/null || source venv/bin/activate
pytest tests/vesta/test_raw_refs.py -q
```

Manual checks:

1. Run a command or tool that produces output above the configured spill limit.
2. Inspect model-facing excerpt.
3. Inspect `<run_dir>/raw/`.
4. Confirm `ledger.md` references the raw payload without embedding it.

Visual inspection:

- Required: inspect `raw/index.md` and `ledger.md` readability.
- Browser automation: not applicable.

## QA And Fix-Forward Gate

If raw output is lost, inlined into the ledger, or stored outside the run, fix
before retrieval, whole-document, worker, or finalization slices. These slices
all rely on stable refs.

## QA Result

Status: pass
Verification command: `uv run --extra dev pytest tests/vesta/test_run_substrate.py tests/vesta/test_ledger_append.py tests/vesta/test_raw_refs.py -q`
Manual checks: raw payload path, raw index, hash, excerpt, and persisted-output
message asserted.
Visual/browser checks: not applicable.
Fix-forward notes: adjusted test to use explicit persistence threshold because
Hermes registry thresholds override `BudgetConfig.default_result_size`.
Residual risk: terminal foreground truncation before generic persistence remains
a later integration concern.

## Out Of Scope

- Cloud sync.
- TTL scheduler.
- Hidden semantic importance classifier.
