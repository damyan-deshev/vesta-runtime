# Slice 09 - Operator Config, Retention, And Prompt-Cache Audit

Status: completed
Mode: AFK after resolved HITL
Blocked by: 02, 03, 04

## User Value

The operator can tune retrieval strictness, whole-document thresholds, raw
retention, and prompt-cache-sensitive behavior without hidden runtime magic.

## Sources

- PRD: Retrieval Discipline, Whole-Document Mode, Raw Retention And Privacy,
  UX Requirements
- User stories: C18, C19, S09, S12, E08, E12, O02, O03, O09
- Hermes overlap: extend `DEFAULT_CONFIG`, `tool_output`, `file_read_max_chars`,
  redaction, and profile-aware paths

## Accepted HITL Decisions

Resolved on 2026-05-16:

- Default retrieval mode: `disciplined`.
- Only escape hatch: `permissive`.
- No retrieval `off` mode in v0.
- Broad-read thresholds: `200` lines, `20_000` bytes, `12_000` estimated tokens.
- Whole-document threshold: `100_000` estimated tokens.
- Whole-document chunk target: `20_000` estimated tokens.
- Raw retention: retain locally by default.
- Purge behavior: preserve refs/manifests as `purged` or `missing`.
- TTL scheduler: out of scope for v0; leave as future config/documented debt.

## Hermes Surfaces To Reuse

- Hermes config loaders and defaults
- existing `tool_output` and file read limit settings
- `security.redact_secrets`
- profile-aware path display

## Vertical Scope

Expose Vesta operator controls:

1. Add config keys for retrieval mode and broad-read thresholds.
2. Add config keys for whole-document threshold/chunk sizing.
3. Add raw retention visibility and purge command or documented local command.
4. Capture relevant config values in `run.md`.
5. Capture prompt-cache-relevant policy state without mutating prompts mid-run.
6. Ensure secrets/API keys are omitted from run metadata.

## Interfaces / Contracts

Config sketch:

```yaml
vesta:
  retrieval:
    mode: disciplined
  whole_document:
    token_threshold: 100000
    max_chunk_tokens: 20000
  raw_retention:
    retain_by_default: true
```

Run metadata must show active effective values, not only defaults.

## Acceptance Criteria

- Default mode is `disciplined`.
- `permissive` can be selected without adding an `off` mode.
- Whole-document thresholds are configurable.
- Purged raw payload refs remain visible as purged/missing, not silently broken.
- Runtime prompt/tool surface remains stable across config changes inside a run.

## Verification

Command target once implemented:

```bash
source .venv/bin/activate 2>/dev/null || source venv/bin/activate
pytest tests/vesta/test_operator_config.py -q
```

Manual checks:

1. Set retrieval mode to `permissive`.
2. Start a run and inspect effective config in `run.md`.
3. Purge a raw payload and confirm manifests update.
4. Confirm no secret values appear in run metadata.

Visual inspection:

- Required: inspect config display and run metadata readability.
- Browser/TUI check: manual-required if controls are only CLI/config.

## QA And Fix-Forward Gate

If config behavior is hidden, secrets leak, or prompt/tool surface mutates
dynamically, fix before control-plane or handoff slices. Defaults above are
accepted; do not re-ask unless implementation discovers a concrete blocker.

## Out Of Scope

- Polished settings UI.
- Cloud retention sync.
- Final TTL scheduler.

## QA Result

Status: pass
Verification command: `uv run --extra dev pytest tests/vesta -q`
Manual checks: Inspected `run.md` config snapshot behavior and raw purge
manifest preservation through tests.
Visual/browser checks: not applicable; no UI in v0.
Fix-forward notes: Added `purge_preserves_manifest` config default while adding
the purge tool so the accepted retention decision is visible in config.
Residual risk: No TTL scheduler and no polished config UI; both are documented
out of scope for v0.
