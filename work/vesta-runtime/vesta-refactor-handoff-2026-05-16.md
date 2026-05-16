# Vesta Refactor Handoff - 2026-05-16

This is a fresh-context handoff for a future coding agent working on
`/Users/damyandeshev/projects/vesta-runtime`.

The goal is not to redesign Vesta from scratch. The goal is to continue from
the observed live eval facts below, preserve the working Vesta surfaces, and
repair the concrete failure modes found during testing.

## Current Repo / Environment

- Repo: `/Users/damyandeshev/projects/vesta-runtime`
- Latest inspected commit during eval: `94a22f9ac Add Vesta runtime state substrate`
- Primary eval ledger:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/vesta-live-eval-2026-05-16.md`
- Isolated eval Hermes home:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16`
- Isolated eval config:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/config.yaml`
- Local model router: `http://192.168.1.117:1234`
- Main live model used for Vesta eval:
  `Qwen3.6-27B-MTP-Q6_K`, observed `ctx-size=196608`
- Validator/delegation lane configured:
  `Qwen3.6-35B-A3B-MTP-UD-Q8_K_XL`, observed `ctx-size=65536`
- Llama telemetry endpoint shape:
  `curl 'http://192.168.1.117:1234/slots?model=Qwen3.6-27B-MTP-Q6_K'`
- Python environment: use `.venv`.

Important local instruction: use `.venv`; do not install Python packages into
the OS environment.

## Current Worktree State At Handoff Creation

The Vesta source files were not edited during the eval. The visible dirty state
was generated eval material:

```text
?? work/vesta-runtime/live-eval-artifacts/
?? work/vesta-runtime/live-eval-hermes-home-2026-05-16/
?? work/vesta-runtime/t09-vesta-live-smoke-prompt.md
?? work/vesta-runtime/vesta-live-eval-2026-05-16.md
```

This handoff file is also an eval artifact and is not intended for upstream git
unless the user says otherwise.

## Baseline Comparison: Original Hermes vs Vesta

Observed positive delta for Vesta over original Hermes/Hermes-agent:

- Vesta creates a file-backed run directory at session start.
- It seeds `run.md`, `ledger.md`, `artifact-manifest.md`, `worker-state.md`,
  `validator-result.md`, `control-plane.md`, `handoff.md`, and `raw/index.md`.
- It provides Vesta tools for durable state:
  `ledger_append`, `artifact_record`, `finalize_run`,
  `worker_state_record`, `coding_eval_start`, `coding_eval_capture`,
  `whole_document_read`, `control_plane_snapshot`, `handoff_generate`,
  `validator_result_record`, and raw ref handling.
- It has working surfaces that original Hermes did not expose in this form:
  copied-workspace coding eval, worker parent-acceptance gates,
  whole-document chunking with raw refs, finalization packets, and recovery
  handoffs from run files.

Observed negative/new-risk delta:

- Vesta now has durable state, so state correctness matters. Several failures
  are not model-quality problems; they are runtime-state semantics problems.
- Artifact status and finalization are currently the highest-risk area.
- Retrieval discipline exists, but its locator predicate is too coarse for
  real research discipline.

## Eval Suite Summary

Primary ledger:
`/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/vesta-live-eval-2026-05-16.md`

Test statuses from that ledger:

```text
T00 Baseline Vesta unit pack                         passed
T01 CLI/provider preflight and run creation          passed_with_observations
T02 Real one-shot research run with Vesta tools      failed_observed
T03 Retrieval discipline on copied source tree       failed_observed
T04 Forced session rotation / resume packet          passed_with_observations
T05 Artifact/finalization honesty                    failed_observed
T06 Worker-state and parent acceptance pressure      passed
T07 Copied-workspace coding eval on real source      passed_with_observations
T08 Whole-document research path                     passed
T09 Multi-faceted live research smoke                partial_success_blocked
T10 Control-plane snapshot and handoff recovery      passed
```

Core deterministic command used at the start:

```bash
source .venv/bin/activate && python -m pytest tests/vesta -q
```

Result at eval time: `41 passed in 4.33s`.

## Positive Behaviors To Preserve

These are not theoretical. They were exercised during the eval.

### Worker Parent-Acceptance Gate Works

Run:
`/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t06_worker_gate`

Observed:

- A completed worker with material claims and an existing artifact blocked
  finalization when parent acceptance and spot audit were absent.
- Blockers:
  `worker_parent_acceptance_missing`,
  `worker_claim_audit_missing`
- After recording `parent_acceptance="accepted"` and a spot audit,
  finalization returned `accepted`.

Do not regress this behavior.

### Copied-Workspace Coding Eval Works

Run:
`/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t07_real_slice`

Eval file:
`/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t07_real_slice/evals/eval_8aaa169b3d/eval.md`

Observed:

- Original source slice copied:
  `/Users/damyandeshev/projects/vesta-runtime/vesta_runtime`
- Eval workspace was under the run directory.
- Modified copied `retrieval.py`, ran `py_compile`, and captured result.
- Original `vesta_runtime/retrieval.py` hash remained unchanged.
- Diff raw ref:
  `raw/eval_8aaa169b3d_diff.txt`
- Verification raw ref:
  `raw/eval_8aaa169b3d_verification.txt`
- Verdict was `accepted`.

Observed polish issue:

- `eval.md` still has the initial top-level `Final Verdict: pending` and later
  appends `## Captured Result` with `Final Verdict: accepted`.
- This is readable but ambiguous for simple parsers and quick scanning.

### Whole-Document Chunking Works

Run:
`/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t08_whole_doc`

Source:
`/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-artifacts/t08-large-doc.md`

Observed:

- Source size: `508815` chars.
- Estimated tokens: `127203`.
- Config threshold: `100000`.
- Result: `chunking_reason=over_threshold`, `chunk_count=7`.
- Raw chunks were written under the run `raw/` directory.
- `raw/index.md` records source, line range, objective, hash, and size.
- Ledger has `Document chunk 1/7` through `Document chunk 7/7` plus
  `Whole-document rolling recap`.
- `prior_recap_chars` increased across chunks, confirming carry-forward state.

Do not replace this with raw whole-document prompt loading.

### Control Plane And Handoff Work For Recovery

Blocked T09 run:
`/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_171242_6e094f`

Control plane:
`/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_171242_6e094f/control-plane.md`

Handoff:
`/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_171242_6e094f/handoff.md`

Observed:

- Control plane reported `Finalization Status: blocked`, not success.
- Handoff said source is Vesta run files, not transcript memory.
- Handoff preserved the artifact manifest contradiction and next action.

This is a useful recovery surface and should be preserved.

## Failure / Refactor Targets

The sections below are facts from observed runs. Implementation decisions are
left to the coding agent.

### 1. Artifact `exists` Can Be False And Still Finalize Accepted

Evidence:

- T02 live run:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164740_6ffb61`
- T05 runtime probe:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t05_false_exists`

T02 observed:

- Expected report:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-artifacts/t02-vesta-harness-surface-research.md`
- File was not created.
- `artifact-manifest.md` still got a second entry for the same path with
  `Status: exists`.
- `finalization.md` was not created.
- Session ended on a tool result and CLI exited `0`.

T05 deterministic probe observed:

- Recorded missing-on-disk artifact as `status="exists"`:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-artifacts/t05-never-created.md`
- Called `write_finalization(...)` with a non-code skip reason.
- `artifact_exists_on_disk=false`
- Finalization verdict: `accepted`
- Blockers: `[]`
- `finalization.md` says `Missing Artifacts: - none recorded`.

Likely relevant files:

- `/Users/damyandeshev/projects/vesta-runtime/vesta_runtime/state.py`
  - `record_artifact`
  - `_artifact_blocks`
  - `write_finalization`
- `/Users/damyandeshev/projects/vesta-runtime/tools/vesta_tools.py`
  - `artifact_record`
  - `finalize_run`
- Tests:
  `/Users/damyandeshev/projects/vesta-runtime/tests/vesta/test_finalization.py`

Observed invariant that is currently false:

- A filesystem-backed artifact should not become trusted `exists` state unless
  the path actually exists, or unless the status explicitly means
  "unverified/model-claimed exists".

### 2. Older `expected` Artifact Blocks After Later `exists`

Evidence:

- T09 live run:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_171242_6e094f`
- Artifact report:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-artifacts/t09-vesta-multisurface-smoke.md`
- Artifact manifest:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_171242_6e094f/artifact-manifest.md`

Manifest excerpt:

```text
### art_5259e2143c
- Path: `work/vesta-runtime/live-eval-artifacts/t09-vesta-multisurface-smoke.md`
- Status: `expected`
- Recorded At: `2026-05-16T17:14:05.598828+03:00`

### art_dae2e16247
- Path: `work/vesta-runtime/live-eval-artifacts/t09-vesta-multisurface-smoke.md`
- Status: `exists`
- Recorded At: `2026-05-16T17:15:54.388191+03:00`
```

Observed:

- File exists on disk.
- Artifact content is acceptable for a smoke test.
- Finalization remained `blocked`.
- `Missing Artifacts` listed the old `expected` entry.
- The model retried finalization once and still got `blocked`.
- The model did not hide the blocker in its final answer.

Likely relevant files:

- `/Users/damyandeshev/projects/vesta-runtime/vesta_runtime/state.py`
  - `_artifact_blocks`
  - `write_finalization`
  - artifact path normalization / status resolution
- Tests:
  `/Users/damyandeshev/projects/vesta-runtime/tests/vesta/test_finalization.py`

Observed invariant that is currently false:

- Finalization should resolve artifact state by stable artifact identity or
  canonical path and latest status, not by treating every historical manifest
  row independently.

### 3. One-Shot CLI Can Exit `0` With Missing Deliverable And No Final Answer

Evidence:

- T02 live run:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164740_6ffb61`
- Session:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/sessions/session_20260516_164740_8b2735.json`

Observed:

- Command exited with code `0` after roughly 15 minutes.
- CLI stdout was empty.
- Final observed llama state for the last turn hit hard generation cap:
  `n_decoded=2048`, `n_remain=0`.
- Session had `61` messages.
- Session ended on a tool result from `artifact_record`.
- There was no final assistant answer in the session file.
- Expected report file was not created.
- `finalization.md` and `resume-packet.md` were not created.
- `logs/errors.log` was empty.

This is not necessarily a Vesta-only bug; it may involve the Hermes CLI/run
loop. But Vesta's purpose is to make this non-silent.

Observed invariant that is currently false:

- A material run with expected artifacts should not look like a clean success
  if it ends on a tool result, has no final assistant response, has missing
  artifacts, or hits max-token/max-iteration conditions.

Likely investigation areas:

- Hermes one-shot CLI / `-z` execution path.
- Vesta run-end/finalization hook opportunities.
- Whether Vesta can write a failure/finalization packet from run state when the
  agent loop ends without a valid final response.

### 4. Retrieval Locator History Is Too Coarse

Evidence:

- T03 runtime probe:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t03_retrieval_scope`

Observed:

- Broad `read_file(limit=500)` on `work/vesta-runtime/prd.md` without any
  locator was blocked as expected.
- A zero-result `search_files` call in the same `task_id` then allowed the same
  broad read.
- An unrelated successful `search_files` call against `README.md` also allowed
  a broad read of `work/vesta-runtime/prd.md`.
- The run ledger remained empty.

Relevant source fact:

- `vesta_runtime/retrieval.py` uses `has_locator_history(task_id) -> bool`.
- `tools/file_tools.py` records every `search_files` call as locator history
  for the task.
- Current allowance is not scoped to file path, source area, result count,
  claim id, question id, or line window.

Likely relevant files:

- `/Users/damyandeshev/projects/vesta-runtime/vesta_runtime/retrieval.py`
- `/Users/damyandeshev/projects/vesta-runtime/tools/file_tools.py`
- Tests:
  `/Users/damyandeshev/projects/vesta-runtime/tests/vesta/test_retrieval_policy.py`

Observed invariant that is currently false:

- Locator-first permission should be tied to relevant locator work, not to the
  mere existence of any previous search in the task.

### 5. Allowed Broad Reads In Disciplined Mode Are Not Auditable State

Evidence:

- T02 live run had 9 `read_file` results with `_vesta_retrieval.broad=true`.
- T03 direct probe allowed broad reads after locator history, but ledger stayed
  empty.
- In permissive mode, code appears to record broad reads. In disciplined mode,
  broad reads allowed after locator/coverage/reason are only annotated in tool
  output.

Observed invariant to consider:

- Broad reads that exceed thresholds, especially in `disciplined` mode, should
  probably become durable/auditable run state when they are allowed.

Implementation is not prescribed here. The fact is that the state is currently
not durable unless another component records it.

### 6. Resume Packet Keeps Ledger Excerpt But Top-Level Pressure Is Generic

Evidence:

- T04 runtime probe:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t04_rotation_pressure`

Observed:

- Session rotation wrote checkpoint and `resume-packet.md`.
- Resume packet included new session id.
- Ledger excerpt included unfinished artifact path and a model-authored next
  action.
- Top-level resume `Objective` was:
  `See ledger Objective section.`
- Top-level resume `Next Action` was:
  `Consult ledger and continue active work.`

Likely relevant file:

- `/Users/damyandeshev/projects/vesta-runtime/vesta_runtime/state.py`
  - `write_resume_packet`
  - `record_session_rotation`

Observed invariant to consider:

- If active commitments/artifacts/gaps exist, the strongest task pressure
  should probably be promoted into top-level resume fields, not only buried in
  a ledger excerpt.

### 7. Initial Run Objective / Next Action Remain Unresolved

Evidence:

- T01, T02, T03, and T04 run ledgers had:
  `Objective: unresolved`
  and
  `Next Action: unresolved`
- This occurred even for material one-shot prompts where the objective and
  expected artifact were known.

Likely relevant file:

- `/Users/damyandeshev/projects/vesta-runtime/vesta_runtime/state.py`
  - run seed rendering
  - current-run creation
  - whether initial prompt/objective is available to Vesta at session start

Observed effect:

- Recovery and compaction pressure are weaker when the top-level ledger seed is
  unresolved and only later entries carry the task.

### 8. Run Metadata Provider Label Is Less Specific Than Operator Config

Evidence:

- T01 smoke run `run.md` captured:
  `Provider: custom`
- Operator-facing invocation used:
  `--provider custom:vesta-local-llama`
- Model and base URL were still recoverable from config/session state.

This is lower priority than artifact/finalization and retrieval. It matters
for operator clarity in multi-model local evals.

## Test Commands Used During Eval

Use `.venv`.

Core slices:

```bash
source .venv/bin/activate && python -m pytest tests/vesta -q
```

Specific commands:

```bash
HERMES_HOME=/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16 \
zsh -lc 'source .venv/bin/activate && python -m pytest tests/vesta/test_retrieval_policy.py -q'

HERMES_HOME=/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16 \
zsh -lc 'source .venv/bin/activate && python -m pytest tests/vesta/test_compaction_resume.py -q'

HERMES_HOME=/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16 \
zsh -lc 'source .venv/bin/activate && python -m pytest tests/vesta/test_finalization.py -q'

HERMES_HOME=/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16 \
zsh -lc 'source .venv/bin/activate && python -m pytest tests/vesta/test_worker_state.py -q'

HERMES_HOME=/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16 \
zsh -lc 'source .venv/bin/activate && python -m pytest tests/vesta/test_coding_eval_run.py -q'

HERMES_HOME=/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16 \
zsh -lc 'source .venv/bin/activate && python -m pytest tests/vesta/test_whole_document.py -q'

HERMES_HOME=/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16 \
zsh -lc 'source .venv/bin/activate && python -m pytest tests/vesta/test_control_plane_visibility.py tests/vesta/test_end_to_end_regression.py -q'
```

Live T09 prompt:

```bash
HERMES_HOME=/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16 \
zsh -lc 'source .venv/bin/activate && hermes -z "$(cat work/vesta-runtime/t09-vesta-live-smoke-prompt.md)" --model Qwen3.6-27B-MTP-Q6_K --provider custom:vesta-local-llama -t hermes-cli'
```

Prompt file:
`/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/t09-vesta-live-smoke-prompt.md`

## Suggested Refactor Order From Observed Risk

This is prioritization from observed facts, not an implementation design.

1. Artifact state semantics and finalization correctness.
2. One-shot run-end failure surfacing for missing artifacts / ended-on-tool /
   no-final-answer / max-token conditions.
3. Retrieval locator scoping and broad-read auditability.
4. Resume packet top-level objective/next-action pressure.
5. Coding eval verdict presentation.
6. Lower-priority run metadata clarity such as provider alias preservation.

## Acceptance Checks After Refactor

Minimum post-refactor checks should include:

- Existing `tests/vesta -q`.
- A new test where `artifact_record(status="exists")` is called on a missing
  filesystem path. It should not produce accepted finalization.
- A new test where an artifact is first `expected`, then actually written and
  recorded `exists`; finalization should not block on the old expected row.
- A retrieval test where zero-result/unrelated `search_files` does not unlock
  broad read elsewhere.
- A retrieval test where relevant locator history still allows a broad read
  when appropriate.
- A T09-style live smoke rerun after artifact-state fixes.
- A T02-style live one-shot rerun after run-end failure surfacing exists.

Larger tests worth running only after the above is fixed:

- Forced live compaction/resume with active expected artifact.
- Worker delegation live test with 27B parent and 35B verifier/worker.
- 60-90 minute long run with control-plane/handoff checkpoints.
- Copied-workspace coding eval on a real private codebase copy.

## Important Operator Notes

- Do not interpret quiet Hermes stdout as stuck while llama telemetry shows an
  active or changing task.
- During T09, the first model turn appeared stuck at `n_decoded=2048`,
  `n_remain=0`, but the harness later continued into tool calls and completed
  useful work.
- For live runs, monitor:
  `curl 'http://192.168.1.117:1234/slots?model=Qwen3.6-27B-MTP-Q6_K'`
- At the end of the eval, the 27B slot was idle and no Hermes process remained
  live.

## Path Index

Primary eval ledger:

`/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/vesta-live-eval-2026-05-16.md`

T09 smoke report:

`/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-artifacts/t09-vesta-multisurface-smoke.md`

T09 control plane:

`/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_171242_6e094f/control-plane.md`

T09 handoff:

`/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_171242_6e094f/handoff.md`

T02 failed live run:

`/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164740_6ffb61`

T03 retrieval run:

`/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t03_retrieval_scope`

T05 false-exists run:

`/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t05_false_exists`

T07 copied eval:

`/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t07_real_slice/evals/eval_8aaa169b3d/eval.md`

T08 whole document run:

`/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t08_whole_doc`

