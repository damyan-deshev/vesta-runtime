# Slice 03 - Retrieval Policy And Broad-Read Repair Gates

Status: ready
Mode: AFK
Blocked by: 00, 01, 02

## User Value

Normal source work defaults to locator-first retrieval, preserving local prompt
cache and context, while whole-document/permissive escape hatches stay possible.

## Sources

- PRD: Retrieval Discipline, UX Requirements
- User stories: C14, C18, C19, S10, S11, E05, E07, E08, E12, O02
- Hermes overlap: extend `search_files`, `read_file(offset, limit)`, read
  dedup, output caps, pre-tool hooks, and config plumbing

## Hermes Surfaces To Reuse

- `search_files`
- `read_file` offset/limit behavior
- repeated-read warnings/blocking
- pre-tool hooks that can repair or block
- `DEFAULT_CONFIG` and tool output settings

## Vertical Scope

Implement v0 retrieval policy:

1. Add `disciplined` and `permissive` retrieval modes.
2. Detect broad reads by line count, byte size, token estimate, whole-file
   request, adjacent repeated reads, and post-compaction reread.
3. In `disciplined`, repair broad reads only when locator history,
   complete-coverage need, and escalation reason are all absent.
4. In `permissive`, allow broad reads but write lightweight reason and raw ref.
5. Keep policy resident/stable; do not mutate prompt/tool surface mid-run.

## Interfaces / Contracts

Config sketch:

```yaml
vesta:
  retrieval:
    mode: disciplined
    broad_read_line_threshold: 200
    broad_read_byte_threshold: 20000
    broad_read_token_threshold: 12000
```

Repair result:

```text
Broad read needs locator-first repair: search or justify complete coverage.
```

## Acceptance Criteria

- `disciplined` mode repairs unjustified broad reads.
- A prior `search_files` or locator ref permits a targeted read.
- Complete-coverage intent permits whole-document workflow, not ad hoc broad
  source ingestion.
- `permissive` mode proceeds while recording a reason/ref.
- No `off` mode exists in v0.

## Verification

Command target once implemented:

```bash
source .venv/bin/activate 2>/dev/null || source venv/bin/activate
pytest tests/vesta/test_retrieval_policy.py -q
```

Manual checks:

1. Try a whole-file source read without locator history in `disciplined`.
2. Confirm repair message.
3. Run locator search, then a narrow read.
4. Switch to `permissive` and confirm broad read proceeds with a ledger reason.

Visual inspection:

- Required: inspect ledger for concise broad-read reason, not raw dump.
- Browser automation: not applicable unless exposed through dashboard later.

## QA And Fix-Forward Gate

If gate behavior causes user-facing loops, prompt-surface churn, or missing raw
refs, fix before whole-document or compaction slices. Record both the failed
tool call and the repair result.

## QA Result

Status: pass
Verification command: `uv run --extra dev pytest tests/vesta -q`
Manual checks: focused tests cover config defaults, `disciplined` broad-read
block, locator-first repair, declared complete coverage, and `permissive`
ledger recording.
Visual/browser checks: not applicable.
Fix-forward notes: none for this slice.
Residual risk: token estimate is intentionally approximate; exact tokenizer
choice remains later product debt.

## Out Of Scope

- User-facing task profiles.
- Automatic per-turn model routing.
- A complete tokenizer decision for every backend; use an estimator if needed.
