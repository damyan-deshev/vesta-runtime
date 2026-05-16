# Vesta Live Eval - 2026-05-16

Status: complete
Repo: `/Users/damyandeshev/projects/vesta-runtime`
Latest inspected commit: `94a22f9ac Add Vesta runtime state substrate`
Operator: Codex observer

## Goal

Run a disciplined Vesta-only evaluation against the current local fork. This is
not a broad Hermes comparison. The purpose is to see whether Vesta's new durable
runtime substrate works as a real harness surface, not only as unit-tested
helpers.

## Ground Rules

- Keep this repo clean unless a test explicitly requires a generated artifact.
- Use `.venv` for Python commands.
- Run tests one at a time and record command, result, artifact paths, and
  observed failure mode.
- Treat Vesta artifacts as source of truth, not model transcript prose.
- Candidate feedback to the development agent must be specific, evidence-backed,
  and useful enough to act on. Do not add wishlist noise.
- Prefer local/private surfaces. Do not rely on public services unless the test
  explicitly needs current external research.

## Evaluation Questions

1. Does a real Vesta run create durable state before material work?
2. Does retrieval discipline shape model/tool behavior rather than only passing
   unit tests?
3. Does compaction/session rotation preserve task pressure through Vesta state?
4. Does finalization block or qualify missing artifacts, failures, unsupported
   claims, and worker uncertainty?
5. Does copied-workspace eval capture enough evidence for real codebase testing?
6. Do whole-document and non-code research paths work as first-class harness
   surfaces?
7. Is the control-plane/handoff surface useful enough for live operator
   recovery?

## Test Matrix

| ID | Test | Type | Status | Primary Evidence |
|---|---|---|---|---|
| T00 | Baseline Vesta unit pack | deterministic | passed | `python -m pytest tests/vesta -q` -> 41 passed |
| T01 | CLI/provider preflight and Vesta run creation | live harness | passed_with_observations | Hermes config/status, run dir |
| T02 | Real one-shot research run with Vesta tools | live harness/research | failed_observed | `run_20260516_164740_6ffb61`, ledger, missing report |
| T03 | Retrieval discipline on copied source tree | runtime/tool | failed_observed | `run_t03_retrieval_scope`, scoped-locator gap |
| T04 | Forced session rotation / compaction resume state | runtime simulation | passed_with_observations | `run_t04_rotation_pressure/resume-packet.md` |
| T05 | Artifact/finalization honesty | runtime/tool | failed_observed | `run_t05_false_exists/finalization.md` |
| T06 | Worker-state and parent acceptance pressure | runtime/tool | passed | `run_t06_worker_gate`, worker blockers |
| T07 | Copied-workspace coding eval on real repo copy | runtime/tool | passed_with_observations | `run_t07_real_slice/evals/eval_8aaa169b3d/eval.md` |
| T08 | Whole-document research path | runtime/tool/research | passed | `run_t08_whole_doc`, 7 raw chunks |
| T09 | Multi-faceted harness research smoke | live harness/research | partial_success_blocked | `t09-vesta-multisurface-smoke.md`, manifest state bug |
| T10 | Control-plane snapshot and handoff recovery | runtime/tool | passed | `run_20260516_171242_6e094f/control-plane.md`, `handoff.md` |

## Execution Log

### 2026-05-16T16:40:34+03:00 - Plan Created

- Created this eval plan.
- Initial repo status before plan creation was clean.

### 2026-05-16T16:41:02+03:00 - T00 Baseline Vesta Unit Pack

- Command: `source .venv/bin/activate && python -m pytest tests/vesta -q`
- Result: pass, `41 passed in 4.33s`.
- Note: using `python -m pytest` avoided the earlier `uv.lock` churn from
  `uv run`.
- Artifact impact: only this eval ledger is untracked.

### 2026-05-16T16:44:11+03:00 - T01 CLI/Provider Preflight And Run Creation

- Direct llama.cpp endpoint preflight:
  `curl http://192.168.1.117:1234/v1/chat/completions` with model
  `Qwen3.6-35B-A3B-MTP-UD-Q8_K_XL` returned `vesta-preflight-ok`.
- Created isolated Hermes home:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16`
- Configured local custom provider in that home only. Real user
  `~/.hermes/config.yaml` was not modified.
- First command attempt was wrong:
  `HERMES_HOME=... source .venv/bin/activate && hermes ...` only scoped
  `HERMES_HOME` to `source`, not the later `hermes` command.
- Second command attempt was wrong:
  `-t vesta` is not a valid Hermes toolset alias, even though Vesta tools are
  registered in the core tool list.
- Corrected live smoke command:
  `HERMES_HOME=/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16 zsh -lc 'source .venv/bin/activate && hermes -z "Reply with exactly: vesta-oneshot-ok" --model Qwen3.6-35B-A3B-MTP-UD-Q8_K_XL --provider custom:vesta-local-llama -t hermes-cli'`
- Result: pass, final response was `vesta-oneshot-ok`.
- Vesta run created:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164333_565017`
- Run files seeded: `run.md`, `ledger.md`, `raw/index.md`,
  `artifact-manifest.md`, `worker-state.md`, `validator-result.md`,
  `control-plane.md`, `handoff.md`.
- Observation: `run.md` captured provider as `custom`, not
  `custom:vesta-local-llama`; model and base URL were still captured via
  session JSON/config, but the run-level provider label is less specific than
  the operator-facing config.
- Observation: the first prompt was known to the runtime, but `ledger.md`
  remained `Objective: unresolved` and `Next Action: unresolved`. This may be
  acceptable for casual no-tool chat, but it is worth watching in material
  tasks.

### 2026-05-16T16:45:29+03:00 - Model Lane Correction

- User clarified intended local model roles:
  - `Qwen3.6-27B-MTP-Q6_K`: larger-context main model.
  - `Qwen3.6-35B-A3B-MTP-UD-Q8_K_XL`: faster MoE, less smart, useful as
    verifier/validator lane.
- `/v1/models` confirmed both are live on `192.168.1.117:1234`.
- Observed live ctx sizes from the llama.cpp router:
  - 27B: `ctx-size=196608`, status `loaded`.
  - 35B: `ctx-size=65536`, status `loaded`.
- Updated isolated eval config so the main model is 27B and the delegation lane
  points at 35B. The earlier 35B `vesta-oneshot-ok` run remains a connectivity
  smoke, not the main model baseline.

### 2026-05-16T16:47:05+03:00 - 27B Main Smoke And Telemetry Rule

- Command:
  `HERMES_HOME=/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16 zsh -lc 'source .venv/bin/activate && hermes -z "Reply with exactly: vesta-27b-main-ok" --model Qwen3.6-27B-MTP-Q6_K --provider custom:vesta-local-llama -t hermes-cli'`
- Result: pass, final response was `vesta-27b-main-ok`.
- The first polling attempt against `/slots` on the router failed with
  `model name is missing from the request`.
- Correct telemetry endpoint shape:
  `curl 'http://192.168.1.117:1234/slots?model=Qwen3.6-27B-MTP-Q6_K'`
  and equivalent for the 35B validator lane.
- Direct per-model llama.cpp ports from `/v1/models` are bound to
  `127.0.0.1` on the llama host and are not reachable from this Mac.
- Operational rule for the rest of this eval: do not treat quiet Hermes stdout
  as a stuck run while the llama router shows a recent active task, decoded
  tokens, prompt progress, or a non-error slot state.

### 2026-05-16T16:52:54+03:00 - T02 In Progress Observation

- T02 process is still live; Hermes stdout is quiet, but the 27B llama slot is
  actively processing new tasks.
- Active run:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164740_6ffb61`
- The run has recorded the expected report through `artifact_record`, but the
  artifact does not exist yet:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-artifacts/t02-vesta-harness-surface-research.md`
- Session JSON shows real tool use: `search_files`, `read_file`, and Vesta
  artifact tooling. This is not a pure prose response.
- Early read-discipline signal: despite the prompt asking for narrow
  inspection, the assistant said it had "got the full ledger design" and then
  read the `tools/vesta_tools.py` schema block from the top. This may be a
  useful pressure point for the retrieval-policy tests, but T02 is not complete
  yet.

### 2026-05-16T17:02:31+03:00 - T02 Completed With Missing Deliverable

- T02 command exited with code `0` after roughly 15 minutes.
- CLI stdout was empty.
- The final observed llama slot state for 27B showed the last model turn ended
  at the hard generation cap: `n_decoded=2048`, `n_remain=0`.
- Session had `61` messages and ended on a tool result from `artifact_record`;
  there was no final assistant answer in the session file.
- Actual model tool calls recorded:
  - `search_files`: 16
  - `read_file`: 9
  - `ledger_append`: 2
  - `artifact_record`: 2
  - `terminal`: 1
- The run did satisfy part of the contract: it used tools, recorded one
  supported claim and one gap in `ledger.md`, and gathered evidence from local
  source files.
- It did not satisfy the core deliverable:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-artifacts/t02-vesta-harness-surface-research.md`
  was not created.
- `artifact-manifest.md` nevertheless contains a second entry for the same path
  with `Status: exists`.
- `finalization.md` and `resume-packet.md` were not created, and
  `validator-result.md` remained `Validator Status: absent`.
- `logs/errors.log` stayed empty, so this surfaced as a clean-but-incomplete
  run rather than a logged runtime error.
- Retrieval discipline observation: all 9 `read_file` results carried
  `_vesta_retrieval.broad=true` in disciplined mode. The broad reasons included
  line-count, file-size, and token-estimate threshold breaches, but the tool
  allowed the reads rather than repairing or requiring an escalation reason.

### 2026-05-16T17:05:15+03:00 - T03 Retrieval Discipline Scope Check

- Command:
  `HERMES_HOME=/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16 zsh -lc 'source .venv/bin/activate && python -m pytest tests/vesta/test_retrieval_policy.py -q'`
- Result: pass, `4 passed in 3.32s`.
- Direct runtime probe then created:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t03_retrieval_scope`
- Probe result:
  - broad `read_file(limit=500)` on `work/vesta-runtime/prd.md` without any
    locator was blocked as expected;
  - a zero-result `search_files` call in the same `task_id` then allowed the
    same broad read;
  - an unrelated successful `search_files` call against `README.md` also
    allowed a broad read of `work/vesta-runtime/prd.md`.
- Root cause from source:
  `vesta_runtime/retrieval.py` uses `has_locator_history(task_id) -> bool`,
  while `tools/file_tools.py` records every `search_files` call as locator
  history for the task. The allowance is not scoped to file path, source area,
  result count, claim id, or line window.
- The T03 ledger remained empty. In disciplined mode, allowed broad reads are
  annotated in the tool result, but no ledger entry records the broad read. That
  makes broad-read behavior harder to audit after the session.

### 2026-05-16T17:06:33+03:00 - T04 Rotation / Resume Packet

- Command:
  `HERMES_HOME=/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16 zsh -lc 'source .venv/bin/activate && python -m pytest tests/vesta/test_compaction_resume.py -q'`
- Result: pass, `2 passed in 1.00s`.
- Direct runtime probe created:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t04_rotation_pressure`
- Probe setup: active commitment plus expected missing artifact, then
  `record_session_rotation(old_session_id="session_t04_old",
  new_session_id="session_t04_new", reason="forced_t04_rotation")`.
- Good result:
  - `resume-packet.md` was created;
  - resume packet names the new Hermes session id;
  - ledger contains a `checkpoint` entry for session rotation;
  - recent ledger excerpt in the resume packet includes the unfinished artifact
    path and the model-authored next action for that commitment.
- Weak result:
  - top-level resume `Objective` is still `See ledger Objective section.`;
  - top-level resume `Next Action` is generic:
    `Consult ledger and continue active work.`;
  - the exact unfinished-artifact pressure survives only inside the ledger
    excerpt, not as the single top-level next action.

### 2026-05-16T17:07:50+03:00 - T05 Artifact / Finalization Honesty

- Command:
  `HERMES_HOME=/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16 zsh -lc 'source .venv/bin/activate && python -m pytest tests/vesta/test_finalization.py -q'`
- Result: pass, `3 passed in 1.32s`.
- Direct runtime probe created:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t05_false_exists`
- Probe: recorded missing-on-disk artifact
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-artifacts/t05-never-created.md`
  with `status="exists"`, then called `write_finalization(...)` with a non-code
  skip reason.
- Result:
  - `artifact_exists_on_disk=false`;
  - finalization verdict was `accepted`;
  - blockers were `[]`;
  - `finalization.md` says `Missing Artifacts: - none recorded`.
- Root finding: finalization trusts the manifest status. It detects
  `expected`/`missing`, but does not re-stat `exists` artifact paths before
  accepting a run.

### 2026-05-16T17:08:28+03:00 - T06 Worker State / Parent Acceptance

- Command:
  `HERMES_HOME=/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16 zsh -lc 'source .venv/bin/activate && python -m pytest tests/vesta/test_worker_state.py -q'`
- Result: pass, `4 passed in 1.31s`.
- Direct runtime probe created:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t06_worker_gate`
- Probe result:
  - completed worker with material claim, existing artifact, but no parent
    acceptance/spot audit produced `blocked`;
  - blockers were `worker_parent_acceptance_missing` and
    `worker_claim_audit_missing`;
  - after recording `parent_acceptance="accepted"` and a spot audit,
    finalization returned `accepted`.
- This surface behaves like real harness pressure: a plausible worker result is
  not accepted only because it exists.

### 2026-05-16T17:10:14+03:00 - T07 Copied-Workspace Coding Eval

- Command:
  `HERMES_HOME=/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16 zsh -lc 'source .venv/bin/activate && python -m pytest tests/vesta/test_coding_eval_run.py -q'`
- Result: pass, `4 passed in 1.30s`.
- Direct real-source-slice probe created:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t07_real_slice`
- Original workspace copied:
  `/Users/damyandeshev/projects/vesta-runtime/vesta_runtime`
- Eval workspace:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t07_real_slice/evals/eval_8aaa169b3d/workspace`
- Probe changed only copied `retrieval.py`, ran `py_compile`, then captured
  eval result.
- Result:
  - original `vesta_runtime/retrieval.py` hash was unchanged;
  - verification exit status was `0`;
  - eval verdict was `accepted`;
  - diff and verification were captured as raw refs:
    `raw/eval_8aaa169b3d_diff.txt` and
    `raw/eval_8aaa169b3d_verification.txt`.
- Observation: `eval.md` still has the initial top-level
  `Final Verdict: pending` and later appends `## Captured Result` with
  `Final Verdict: accepted`. This is readable, but ambiguous for simple
  parsers and quick human scanning.

### 2026-05-16T17:11:44+03:00 - T08 Whole-Document Research Path

- Command:
  `HERMES_HOME=/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16 zsh -lc 'source .venv/bin/activate && python -m pytest tests/vesta/test_whole_document.py -q'`
- Result: pass, `2 passed in 1.22s`.
- Direct runtime probe created:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t08_whole_doc`
- Source document:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-artifacts/t08-large-doc.md`
- Source size: `508815` chars, estimated `127203` tokens.
- Live config thresholds: `token_threshold=100000`,
  `max_chunk_tokens=20000`.
- Result:
  - `chunking_reason=over_threshold`;
  - `chunk_count=7`;
  - raw chunks were written under run `raw/`;
  - `raw/index.md` records chunk source, line range, objective, hash, and size;
  - ledger has `Document chunk 1/7` through `Document chunk 7/7` and
    `Whole-document rolling recap`;
  - `prior_recap_chars` increased across chunks, confirming carry-forward
    state.
- This is a real non-code/research harness surface: the raw document was not
  dumped into the prompt, but remained recoverable through chunk refs.

### 2026-05-16T17:16:53+03:00 - T09 Small Live Multi-Surface Research Smoke

- Prompt file:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/t09-vesta-live-smoke-prompt.md`
- Command:
  `HERMES_HOME=/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16 zsh -lc 'source .venv/bin/activate && hermes -z "$(cat work/vesta-runtime/t09-vesta-live-smoke-prompt.md)" --model Qwen3.6-27B-MTP-Q6_K --provider custom:vesta-local-llama -t hermes-cli'`
- Active run:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_171242_6e094f`
- Llama telemetry note: the first model turn appeared stuck at
  `n_decoded=2048`, `n_remain=0` for a while, but then the harness continued
  into later tasks and tools. This confirms the operator rule: do not kill a
  local-model run only because stdout is quiet.
- The run used the intended narrow reads and wrote:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-artifacts/t09-vesta-multisurface-smoke.md`
- Artifact content is acceptable for a smoke test: 3 non-coding surfaces,
  2 coding/eval surfaces, 1 caveat, and source refs.
- Ledger contains a supported claim:
  `Vesta is a multi-surface harness`.
- Finalization verdict: `blocked`.
- Root cause: artifact manifest is append-only, but finalization does not
  collapse latest status by artifact path. The manifest has an older
  `expected` entry and a later `exists` entry for the same path; finalization
  still treats the older `expected` entry as missing.
- The model noticed the block and retried finalization once. It did not hide the
  blocker in the final answer.

### 2026-05-16T17:17:58+03:00 - T10 Control Plane / Handoff Recovery

- Command:
  `HERMES_HOME=/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16 zsh -lc 'source .venv/bin/activate && python -m pytest tests/vesta/test_control_plane_visibility.py tests/vesta/test_end_to_end_regression.py -q'`
- Result: pass, `6 passed in 1.26s`.
- Direct recovery probe reused the blocked T09 run:
  `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_171242_6e094f`
- Generated:
  - `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_171242_6e094f/control-plane.md`
  - `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_171242_6e094f/handoff.md`
- Good result:
  - control plane reports `Finalization Status: blocked`, not success;
  - control plane includes run path, ledger path, finalization path, validator
    status, and latest next action;
  - handoff is explicitly sourced from Vesta run files, not transcript memory;
  - handoff preserves the artifact manifest contradiction and gives a concrete
    next action: fix latest-status handling, then rerun finalization.
- This is a useful recovery surface for a new chat/agent after a blocked live
  run.

## Result Summary

- Deterministic Vesta unit surfaces passed in the tested slices.
- The runtime substrate is real enough to support copied-workspace coding eval,
  worker acceptance gates, whole-document chunking, control-plane snapshots, and
  handoff recovery.
- Live 27B one-shot behavior is fragile when the prompt invites extended
  reasoning; T02 missed its deliverable and T09 had an initial max-token turn
  before recovering.
- The most important runtime bugs are around artifact state and finalization:
  false `exists` can be accepted, and old `expected` entries can continue to
  block after later `exists` entries.
- Retrieval discipline exists, but the locator predicate is too broad for real
  research discipline.

Overall: Vesta is worth continuing, but the next dev pass should focus on
artifact/finalization correctness and retrieval scoping before deeper live
agent benchmarks.

## Candidate Dev-Agent Feedback

1. `artifact_record(status="exists")` and/or `write_finalization` should verify
   filesystem-backed artifact paths. T02 produced a manifest entry saying the
   report existed while the file was missing, and T05 showed finalization can
   accept that false `exists` status with no blockers.
2. One-shot CLI runs should not exit `0` when the session ends with unresolved
   expected artifacts and no final assistant response. At minimum, the run
   should write a failure/finalization packet that exposes `ended_on_tool`,
   `missing_artifact`, `max_tokens`, or `max_iterations`.
3. Disciplined retrieval enforcement should scope locator history. T03 showed
   that a zero-result or unrelated `search_files` call in the same `task_id`
   unlocks broad reads elsewhere. `has_locator_history(task_id)` is too coarse;
   consider path/source-area/result-count and/or `claim_id`/`question_id`
   matching before allowing a broad read.
4. Run seeding still leaves `Objective` and `Next Action` as `unresolved` for a
   material one-shot prompt. That weakens recovery and finalization after a
   clean-but-incomplete run.
5. In disciplined mode, allowed broad reads should become auditable state, at
   least when they exceed file-size/token thresholds. T03 allowed broad reads
   after locator history but left the ledger empty.
6. Compaction/session-rotation resume packets should promote the strongest
   active task pressure into top-level fields. T04 preserved the unfinished
   artifact inside the ledger excerpt, but top-level `Objective` and
   `Next Action` were generic.
7. `coding_eval_capture` should update or explicitly supersede the initial
   top-level `Final Verdict: pending` in `eval.md`. T07 produced a valid
   accepted captured result, but the first verdict field stayed pending.
8. Artifact manifest finalization should resolve latest status per artifact
   identity/path. T09 correctly recorded `expected` then `exists` for the same
   report, but finalization still blocked on the old `expected` entry.
