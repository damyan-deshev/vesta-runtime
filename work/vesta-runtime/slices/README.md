# Vesta Runtime Vertical Slices

Date: 2026-05-16
Status: Implemented through Slice 12

Inputs:

- `work/vesta-runtime/prd.md`
- `work/vesta-runtime/user-stories.md`
- `work/vesta-runtime/hermes-surface-overlap.md`

## Execution Rule

Each slice is a local markdown issue. A slice is not complete until its own
verification and QA gate pass. If a test, manual check, or visual inspection
finds an issue, fix forward inside the same slice before starting dependent
slices. Do not mark a downstream slice complete on top of a known broken
upstream contract.

QA evidence should include:

- verification command output or manual check notes;
- generated file paths;
- console/network/accessibility/screenshot evidence for UI/browser slices;
- explicit blocked or manual-required status when a capability is unavailable;
- fix-forward notes for failures found during slice QA.

## Accepted HITL Decisions

Resolved on 2026-05-16. Do not stop implementation to re-ask these unless code
inspection reveals a concrete blocker.

- Retrieval defaults: `disciplined` by default, `permissive` as the only escape
  hatch, no `off` mode.
- Broad-read v0 thresholds: `200` lines, `20_000` bytes, `12_000` estimated
  tokens.
- Whole-document v0 defaults: `100_000` estimated token threshold and `20_000`
  estimated token target chunks.
- Long-document context: chunk N receives prior rolling recap, unresolved
  questions/terms, and objective.
- Raw retention: retain locally by default; purge preserves refs/manifests as
  `purged` or `missing`; no TTL scheduler in v0.
- Control plane: no new UI first. CLI/file inspection is authoritative.
  TUI/ACP/dashboard are smoke-test visibility surfaces after runtime state
  exists.
- QA rule: every slice passes its own tests/manual inspection before dependent
  slices. Browser QA applies only where a browser/dashboard surface exists. Do
  not claim visual QA if browser/vision is unavailable; mark `manual-required`.

## Index

| Slice | Title | Mode | Status | Blocked by | What proves it is done |
|---:|---|---|---|---|---|
| 00 | Run substrate and ledger seed | AFK | completed | none | Starting a Vesta run creates stable `run_id`, run dir, `run.md`, `ledger.md`, and Hermes lineage metadata under active Hermes home. |
| 01 | Ledger append primitive and material state | AFK | completed | 00 | `ledger_append` appends small Markdown entries with runtime ids/timestamps and preserves append-only behavior. |
| 02 | Run-scoped raw evidence refs | AFK | completed | 00, 01 | Large tool output is persisted under run `raw/`, model receives excerpt/ref, and ledger can cite the raw ref. |
| 03 | Retrieval policy and broad-read repair gates | AFK | completed | 00, 01, 02 | `disciplined` mode repairs unjustified broad reads; `permissive` records broad-read reason and proceeds. |
| 04 | Whole-document chunking with rolling recap | AFK | completed | 00, 01, 02, 03 | A long document is chunked, each chunk writes findings, later chunks receive prior recap, and synthesis uses ledger findings. |
| 05 | Ledger-aware compaction and resume packet | AFK | completed | 00, 01, 02 | Hermes compaction lineage produces a Vesta checkpoint and resume packet with non-null next action when work remains. |
| 06 | Artifact commitments and finalization gate | AFK | completed | 00, 01, 02, 05 | Finalization checks objective, artifacts, material claims, gaps, failures, verification/skip reason, and next action. |
| 07 | Worker state and parent acceptance | AFK | completed | 00, 01, 02, 06 | A delegated worker records state/artifacts/gaps/failures and parent acceptance audits material claims. |
| 08 | Copied-repo coding eval with verification capture | AFK | completed | 00, 01, 02, 06 | A coding eval runs in an isolated copied/worktree workspace and captures prompt/config/diff/tests/final verdict. |
| 09 | Operator config, retention, and prompt-cache audit | AFK after resolved HITL | completed | 02, 03, 04 | Retrieval strictness, whole-document thresholds, raw retention, and prompt-cache-relevant metadata are visible in config/run state. |
| 10 | Selective validator contract | AFK | completed | 06, 07, 08 | High-risk work records separated primary/test/validator results without requiring an always-on validator engine. |
| 11 | Control-plane visibility smoke | AFK after resolved HITL, manual QA if UI exists | completed | 00, 06, 07, 09 | TUI/ACP/dashboard surfaces can inspect run/session/worker state without becoming authoritative state. |
| 12 | Handoff and end-to-end regression pack | AFK | completed | 00-11 | A handoff artifact summarizes decisions/state/next action and a regression command exercises the v0 critical path. |

## Common QA Contract

Every slice must include a short local QA record when implemented:

```markdown
## QA Result

Status: pass | fail | blocked | inconclusive
Verification command:
Manual checks:
Visual/browser checks:
Fix-forward notes:
Residual risk:
```

For browser or dashboard checks, follow the browser QA discipline: capture URL,
console errors, failed network requests, DOM/accessibility notes, screenshots
when allowed, and visual review status. If browser automation or vision is not
available, mark that portion as `blocked` or `manual-required`; do not pretend
visual inspection happened.
