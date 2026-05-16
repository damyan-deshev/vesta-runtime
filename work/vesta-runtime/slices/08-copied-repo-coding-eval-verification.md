# Slice 08 - Copied-Repo Coding Eval With Verification Capture

Status: completed
Mode: AFK
Blocked by: 00, 01, 02, 06

## User Value

Coding evals can run without mutating original projects, and final verdicts are
tied to exact prompt/config/diff/test evidence.

## Sources

- PRD: Testing / QA Decisions, Definition Of Done
- User stories: S01, S02, S03, S04, E10, E11, O09, O11
- Hermes overlap: extend `--worktree`, checkpoints, session logs,
  trajectories, redaction, and raw refs

## Hermes Surfaces To Reuse

- CLI `--worktree` where it fits eval needs
- filesystem checkpoints
- terminal/tool outputs
- session logs and trajectories as supporting material
- redaction and checkpoint exclusion patterns

## Vertical Scope

Implement a repeatable coding eval path:

1. Create isolated copied/worktree workspace.
2. Record original path and copied workspace path.
3. Capture prompt, model/provider/config metadata without secrets.
4. Capture diff/patch output.
5. Capture verification commands and outputs.
6. Record failed commands as state.
7. Finalize from artifact/verification state.
8. Keep sensitive excluded paths visible and overridable only deliberately.

## Interfaces / Contracts

Eval run state:

```text
original_workspace:
eval_workspace:
prompt_ref:
config_ref:
diff_ref:
verification:
excluded_paths:
final_verdict:
```

## Acceptance Criteria

- Original repo is not mutated by default.
- Verification output is stored as raw ref and summarized in finalization.
- Failed verification requires skip/failure reason.
- Diff and test evidence are enough for later review.
- Sensitive file exclusions are recorded.

## Verification

Command target once implemented:

```bash
source .venv/bin/activate 2>/dev/null || source venv/bin/activate
pytest tests/vesta/test_coding_eval_run.py -q
```

Manual checks:

1. Run a small fixture repo eval.
2. Confirm original repo remains unchanged.
3. Confirm copied/worktree path is recorded.
4. Inspect diff/test raw refs and final verdict.

Visual inspection:

- Required: inspect generated eval run directory.
- Browser automation: not applicable.

## QA And Fix-Forward Gate

If original workspace mutation or missing verification capture is observed, fix
before validator or end-to-end slices. This slice is the first hard eval
surface.

## Out Of Scope

- Enterprise sandboxing.
- Full benchmark dashboard.
- Always-on validator.

## QA Result

Status: pass
Verification command: `uv run --extra dev pytest tests/vesta -q`
Manual checks: Inspected eval state shape through tests: original workspace
remains unchanged, copied workspace excludes sensitive paths, diff and
verification refs are written.
Visual/browser checks: not applicable.
Fix-forward notes: Implemented copy-based eval first; this keeps the vertical
slice deterministic and leaves deeper CLI `--worktree` orchestration as a later
integration option.
Residual risk: Large real repositories may need smarter copy strategy or native
git worktree mode for speed; v0 records enough state to preserve reviewability.
