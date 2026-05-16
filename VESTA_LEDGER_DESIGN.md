# Vesta Ledger Design

Date: 2026-05-16

## Core Definition

The Vesta ledger is durable runtime state, not a transcript summary and not a
research-report database. It records the operational reality after conversation:
what is known, why it is known, what was decided, what is uncertain, what was
promised, which workers exist, which artifacts exist, and what must happen next.

Formula:

```text
Ledger = durable epistemic + operational + artifact state.
Internal policies decide strictness.
Compaction/resume reads the ledger, not the transcript vibes.
```

The ledger is continuous working memory. It is updated after material actions
while the work is happening; compaction is a consumer of the ledger, not the
moment when the ledger is invented.

## Non-Goals

- Do not store whole transcripts in the ledger.
- Do not inline large tool outputs or full files.
- Do not make separate ledgers for research, coding, ideation, planning, and
  reflection.
- Do not start with a rich ontology that blocks implementation.
- Do not make JSONL/SQL the model-authored surface in v0.

## State Boundaries

- `action`: something the agent/tool did, such as reading `LICENSE`.
- `claim`: something asserted about the world, such as "the license is MIT."
- `artifact`: any durable output or externalized work product, not only code
  artifacts. Examples: report, plan, decision memo, checklist, research note,
  prompt, generated document, calendar/action brief, saved conversation
  synthesis, patch, test result, eval result, or worker handoff.
- `decision`: accepted direction plus rationale and alternatives.
- `gap` / `open_question`: something not yet known.
- `contradiction`: conflicting evidence that may block finalization.
- `commitment`: promised output or follow-up that preserves pressure to finish.
- `worker_state`: delegated work, accepted/rejected workers, output contract,
  status, failures, and next action.

## Entry Shape

Every entry should be append-only and small.

```yaml
ledger_entry:
  id:
  session_id:
  project_id:
  timestamp:
  actor:
    type: user | parent_agent | worker_agent | tool | system
    id:
  entry_type: objective | constraint | assumption | claim | hypothesis |
    interpretation | decision | open_question | gap | contradiction | action |
    artifact | failure | recovery | worker_state | commitment | next_step |
    checkpoint
  status: proposed | active | verified | supported | rejected | superseded |
    unresolved | accepted
  scope: turn | session | task | project | workspace | global
  materiality: low | medium | high | critical
  content:
    statement:
    structured_payload: {}
  provenance:
    source_refs: []
    artifact_refs: []
    tool_refs: []
    message_refs: []
  epistemic:
    confidence:
    basis:
  lifecycle:
    supersedes: []
    superseded_by:
  tags: []
```

## Source References

Source refs point to raw material without swallowing it. Large payloads live in
raw artifact storage with hashes and narrow excerpts.

```yaml
source_ref:
  id:
  source_type: local_file | command | url | tool_output | session | message
  locator:
    path:
    line_start:
    line_end:
    command:
    url:
  content_hash:
  excerpt:
  captured_at:
  full_payload_path:
```

## Raw Capture Policy

Vesta should not classify raw tool outputs semantically at runtime. Hermes'
current pattern is mechanical:

- transcript messages are persisted in SQLite/session logs;
- tool results stay in the transcript unless they exceed size/budget thresholds;
- oversized tool results are spilled to files with preview + path;
- compression later prunes old tool outputs into short summaries.

Vesta should borrow the principle, not necessarily every path name:

- record deterministic tool-call metadata for every tool call in the run;
- spill full raw outputs by mechanical thresholds and aggregate turn budgets;
- store content hash, excerpt, locator, tool name, arguments, exit status when
  available, and runtime timestamp;
- let `ledger_append`, user decisions, artifact contracts, and finalization
  promote raw refs to evidence/source/artifact/failure/contradiction.

Do not add a hidden runtime judge for "this output is important." The model and
user assign meaning through ledger entries; runtime code preserves enough
deterministic material for that meaning to be inspectable.

### Piggyback Implementation

Do not build a separate raw-output pipeline in v0. Piggyback on Hermes'
existing tool-result persistence:

- `maybe_persist_tool_result` already runs after tool execution in both
  sequential and concurrent paths;
- `BudgetConfig` already defines per-result threshold, aggregate turn budget,
  preview size, and per-tool overrides;
- persisted output already returns an in-context preview plus file path;
- compression already understands old tool outputs as things to deduplicate,
  summarize, or prune.

The Vesta extension should be narrow: when a Vesta run is active, make the
existing persisted-output path write to the run's `raw/` directory instead of
only temp storage, and record manifest/source-ref metadata around the same
event. This may require a small storage-dir hook or override in
`tools/tool_result_storage.py`, but it should not duplicate the retention
logic.

Pure plugin capture through `post_tool_call` is less attractive because it sees
raw results before Hermes' persistence/budget pass and would create a parallel
copying policy. Vesta should attach to the existing spill path, not race it.

## Retrieval Discipline

Vesta's default source-reading behavior should be locator-first:

- locate before reading with search, manifests, counts, or file metadata;
- read narrow windows when the task asks for a targeted fact or edit;
- attach broad reads to a claim, question, gap, or explicit user objective;
- record failed paths, zero-match searches, and wrong guesses as negative
  evidence when they matter;
- after compaction, consult `ledger.md` before rereading raw sources.

This is not a user-facing profile. It is part of the resident Vesta contract for
local runtime discipline. The abstract rule is: prefer the smallest source range
that can answer the task honestly.

Full-document reading is still a first-class path, but it should be treated as a
complete-coverage contract. The model may choose it when the user objective or
task semantics require understanding the whole artifact, but it should not use a
whole-file read as the default retrieval move. The resident prompt should avoid
keyword-trigger examples for this decision; examples create brittle local
minima. The model-facing rule should stay semantic: do not read the whole file
unless complete coverage is needed, or unless the model records a short reason
for escalating from locator-first retrieval.

Large whole-document reads should use a chunk/ledger workflow:

1. measure approximate token size before loading the full text into context;
2. split large inputs into proportional chunks when they exceed the configured
   working threshold;
3. read one chunk at a time with the current document objective and accumulated
   prior-chunk recap in context;
4. append a chunk finding to `ledger.md` with source refs and unresolved gaps;
5. update the rolling recap for the next chunk;
6. synthesize from the accumulated ledger;
7. reread the smallest raw range when a high-materiality detail depends on exact
   wording or a chunk summary looks insufficient.

The ledger is the working surface for cross-chunk synthesis, not a replacement
for raw source refs. Chunk summaries may guide reasoning, but important details
must stay recoverable through source locators and raw payload paths.

Chunk processing must preserve document continuity. Many later sections depend
on terminology, setup, methods, assumptions, or claims introduced earlier. The
runtime should therefore pass a compact rolling recap into each subsequent
chunk-processing step:

- document objective and user question;
- document map or section outline when available;
- accumulated recap of prior chunks;
- unresolved terms, claims, contradictions, and open questions;
- current chunk source locator and raw text.

The recap should be reinjected as working context for chunk N, but raw prior
chunks should not be reinjected by default. If the accumulated recap grows too
large, collapse it hierarchically into a shorter document-state recap while
preserving raw refs in the ledger.

### Retrieval Strictness Toggle

Broad-read gates should be exposed as runtime policy, not hidden behavior. The
user should be able to choose the strictness for a run from the UI/TUI/CLI.

Recommended v0 shape:

- `disciplined`: default; broad reads trigger repair-first behavior unless
  complete coverage is semantically justified or declared;
- `permissive`: broad reads are allowed with a lightweight ledger reason and
  raw refs, reducing model/runtime back-and-forth when the user values speed or
  full ingestion over context frugality.

Do not add an `off` mode in v0. `permissive` should be the escape hatch. It
reduces friction without abandoning ledger/raw-reference discipline. A true off
switch can be reconsidered only if permissive mode still creates measurable
workflow drag.

This toggle changes runtime gate behavior and `run.md` state. It should not add
or remove prompt instructions or tools mid-session. The resident prompt can
refer to a stable "current retrieval policy" concept, while the actual policy
value lives in run state and is enforced by tools/gates.

### Broad-Read Gate Semantics

In `disciplined` mode, the broad-read gate should repair only missing context,
not every large read. A broad read proceeds when at least one of these is true:

- there is relevant locator history for the same artifact or source area;
- the user objective or task semantics require complete coverage;
- the model records a short escalation reason tied to a claim, question, gap, or
  objective.

If all three are absent, the tool should return a concise repair instruction:
narrow the read, locate first, or declare complete-coverage/escalation reason.
In `permissive` mode, the runtime allows broad reads with a lightweight ledger
reason and raw refs.

Broad-read detection should be configurable rather than hardcoded. Candidate
signals include requested line count, estimated tokens, file size, whole-file
requests, repeated adjacent reads that effectively reconstruct a file, and
post-compaction rereads of already-referenced material.

### Whole-Document Controls

Whole-document mode begins with token or size estimation before ingestion. If
the artifact exceeds the configured working threshold, Vesta should chunk it and
write chunk findings to the ledger before final synthesis.

The whole-document threshold must be user-controllable. When UI/TUI controls do
not exist yet, expose it through runtime config or CLI and record the missing UI
surface as product debt. Do not bury this as an unchangeable constant; the user
must be able to trade context discipline against speed and hardware capacity.

## Model-Facing Format

The model-facing ledger in v0 should be Markdown:

- canonical file: `ledger.md`;
- append-friendly;
- stable headings and entry IDs;
- human-inspectable;
- resilient when the model writes imperfect text;
- backed by raw payload files for large outputs.

Structured storage can come later as a generated index/cache. The model should
not be asked to directly maintain JSONL or SQL in v0.

## Write Policy

The model should update the ledger after material actions, not after every small
operation.

Write when an action:

- supports or refutes a claim;
- creates, changes, verifies, or misses an artifact;
- records a user/product decision;
- discovers a gap, open question, contradiction, failure, or recovery;
- changes a commitment, worker state, phase, or next action;
- records a high-materiality source reference.

Do not write for noisy mechanics: repeated searches with no new information,
simple directory listings, or micro-steps that do not change operational state.

## v0 Write Primitive

Normal ledger writes should go through `ledger_append`, not direct whole-file
patches.

Minimal model-provided fields:

- `entry_type`
- `title`
- `statement`
- `refs`
- `status`
- `materiality`
- `next_action`

Runtime-provided fields:

- entry id;
- timestamp;
- session id;
- run directory;
- actor.

The timestamp is always generated by runtime/tool code, never by the model.
The same clock path should be used for `created_at`, ledger entries, source
capture times, artifact verification times, worker state updates, checkpoints,
and finalization records. Reuse Hermes' existing `hermes_time.py` /
`hermes_time.now()` path as the migration anchor; later Vesta naming can wrap
or rename it without changing the invariant.

Example rendered Markdown:

```md
### le_0007 - Decision - v0 surface is eval harness first
Status: accepted
Materiality: high
Refs: VESTA_DESIGN_INTERVIEW.md
Statement: The first v0 surface is a repeatable eval/run harness, not CLI/TUI
or ACP.
Next action: Define the expanded runtime/eval implementation package.
```

## Timestamp Invariant

Models do not author timestamps. Any timestamp in `run.md`, `ledger.md`,
`artifact-manifest.md`, `resume-packet.md`, source refs, worker state, or
finalization records must come from one runtime-owned clock path or an explicit
time tool.

Canonical timestamps should be runtime-local RFC3339/ISO-8601 strings with an
explicit offset, for example `2026-05-16T14:32:10+03:00`. This keeps local work
human-readable while remaining unambiguous. UTC can be generated later as a
secondary index/audit field if cross-machine or team workflows need it.

This avoids inconsistent chronology when the model guesses the current time or
uses stale prompt context. The model may request a timestamped write through
`ledger_append`; the runtime supplies the actual timestamp.

## Internal Policies

v0 should not expose user-facing task profiles. Hermes already behaves as one
broad assistant and adapts by tools, skills, prompt content, and guardrails.
Vesta should keep that shape: one resident ledger substrate with internal
policies that change gate behavior from events and run state.

Recommended v0 policies:

- `ledger_core`: always on; records objectives, decisions, claims, gaps,
  commitments, artifacts, worker state, and next action.
- `evidence_policy`: applies when a material claim, research result, audit
  finding, contradiction, or final report is being recorded.
- `artifact_policy`: applies when a promised output, saved note, patch, report,
  handoff, eval result, or generated document is created or expected.
- `verification_policy`: applies when code, configuration, tests, validation, or
  risky operational changes are involved.
- `planning_policy`: applies when the run contains options, tradeoffs,
  sequencing, dependencies, or open product decisions.
- `worker_policy`: applies when any delegated worker/subagent exists.

These policies are runtime rules and finalization checks, not model-visible
mode switches. Do not inject dynamic "now you are in research mode" or "ledger
is now active" text every few turns. Store any active policy state in `run.md`
/ `ledger.md`, and keep the resident prompt stable.

## Activation Model

Ledger activation should be Vesta-native and stable:

- Vesta session: ledger/run protocol and tools are present from the start and
  remain stable for the session;
- Hermes compatibility/debug mode: may run without the Vesta prompt/tool
  surface while the fork is still aligned with upstream.

Hermes is the upstream parent and near-term implementation base, not the
long-term product boundary. In Vesta proper, durable runtime state is a product
feature. Do not classify every turn to decide whether to add ledger
instructions. That adds backend complexity and risks breaking prompt-cache
similarity on local llama.cpp-style backends. Instead:

- create `run_id`, the run directory, `run.md`, and `ledger.md` at session start;
- write `created_at` from the runtime clock, not model text;
- keep `ledger_append` available from the beginning;
- let gate strictness depend on recorded runtime state, such as commitments,
  artifacts, failed tests, workers, contradictions, or high-materiality claims;
- allow casual/low-materiality exchanges to produce little or no ledger content
  without forcing finalization pressure.

This gives Vesta one stable contract: the ledger is available because this is
Vesta. The system avoids a second problem of deciding when to tell the model
that memory exists.

Immediate seed-file creation is intentional. Empty or near-empty files are less
dangerous than a lazy "does this run exist yet?" state machine at compaction,
artifact, worker, and finalization boundaries.

## Session Seed Files

At Vesta session start, create the run directory and seed both files.

`run.md` is runtime metadata/control state. It should include:

- `run_id`;
- runtime-owned `created_at`;
- workspace path and workspace hash;
- active session id and upstream lineage ids;
- model, provider, context-window, and relevant runtime config snapshot;
- ledger path, artifact manifest path, raw output directory;
- current phase, initially `initialized`;
- gate state, initially light/dormant;
- worker lane config, if present.

`ledger.md` is human-facing operational truth. It should include:

- run/session/workspace header;
- initial `session_started` entry;
- objective state, initially unset unless the first user task is already known;
- open gaps, initially none;
- next action, e.g. `await first material task` or the known initial task.

Do not collapse these files. `run.md` answers "what runtime container is this?"
while `ledger.md` answers "what does this run know, decide, owe, and need next?"

## Compaction / Resume Contract

Compaction writes a checkpoint entry and builds a resume packet from active
working state, not prose summary.

Resume packet must include:

- objective;
- current phase;
- active commitments;
- active decisions;
- verified claims;
- open questions and blocking gaps;
- contradictions that block finalization;
- worker status;
- artifact manifest;
- ledger path;
- exactly one next action.

If a deliverable is unfinished, `next_action` must not be `None`.

The continuation should receive a small resume packet and the ledger path. It
should read `ledger.md` before continuing when the packet says the ledger has
material state.

After compaction, the first material action should require resume continuity:
consult the resume packet and `ledger.md` status before continuing. If there is
no unfinished deliverable, commitment, material claim, worker, contradiction, or
expected artifact, Vesta should avoid extra ceremony.

## Hermes Alignment

Use existing Hermes primitives where they already match the desired runtime
shape, but treat them as migration anchors rather than permanent product names:

- `session_id`: existing conversation identity, persisted in SQLite and exposed
  to tools through `HERMES_SESSION_ID`;
- `parent_session_id`: existing lineage edge for compression continuations,
  branches, and child sessions;
- `task_id`: existing tool-isolation key for terminal, browser, file-state, and
  delegated work; CLI/TUI/ACP commonly pass the session id as task id;
- cwd/profile: existing approximation of workspace scope;
- session logs, trajectories, checkpoints, and tool-result persistence:
  existing raw material surfaces that Vesta can reference.

Do not overload Hermes `sessions` as the Vesta run ledger. In v0, create a
small Vesta run layer anchored by `run_id`, `session_id`, and `task_id`, with
file-backed state under a run directory:

```text
run/
  run.md
  ledger.md
  resume-packet.md
  artifact-manifest.md
  raw/
  finalization.md
```

This keeps the design aligned with Hermes: reuse Hermes
session/lineage/tool isolation, but keep Vesta's operational truth in Markdown
artifacts rather than migrating the core SQLite transcript schema.

### Integration Strategy

Vesta v0 should be plugin-first:

- `ledger_append` and related runtime tools live in a plugin/tool layer.
- Run directory creation, artifact manifests, raw payload references, and
  worker-state recording live outside core transcript storage.
- Existing `pre_tool_call`, `post_tool_call`, `pre_llm_call`, `post_llm_call`,
  `on_session_start`, and `on_session_end` hooks should be reused where they
  are enough.
- Direct core patches should be narrow lifecycle hooks where Hermes currently
  has no clean extension point.

The likely first missing lifecycle point is compaction/resume. Hermes already
rotates session IDs during compression and informs the active context engine,
but Vesta needs a ledger checkpoint and resume packet at that boundary. Prefer
adding a small upstreamable hook around compression over replacing the entire
context engine or moving Vesta state into Hermes' SQLite transcript tables.

`run_id` is not the same as Hermes `session_id`. Hermes may rotate the
`session_id` on compression. Vesta should keep one stable `run_id` and record
the active Hermes session lineage inside `run.md` or `ledger.md`.

### Run Storage

Borrow Hermes' profile-aware path convention:

- use `get_hermes_home()` as the only root resolver;
- place Vesta state under the active Hermes profile, not under the OS home
  directly;
- use a module-level base path, analogous to `CHECKPOINT_BASE =
  get_hermes_home() / "checkpoints"`;
- group runs by a deterministic normalized workspace hash, analogous to
  checkpoint project hashes;
- keep a human-readable `workspace.md` or `run.md` next to hashed directories so
  users can inspect paths without decoding hashes.

Recommended v0 shape:

```text
{get_hermes_home()}/vesta/
  workspaces/
    <workspace_hash>/
      workspace.md
      runs/
        <run_id>/
          run.md
          ledger.md
          resume-packet.md
          artifact-manifest.md
          raw/
          finalization.md
```

This follows upstream Hermes behavior closely: persistent state belongs under
the active profile, repo working directories stay clean by default, and path
display should use `display_hermes_home()` in user-facing messages.

### Worker Model Lane

Hermes already has the right primitive for v0 worker routing:

- `delegation.model`;
- `delegation.provider`;
- `delegation.base_url`;
- `delegation.api_key`;
- `delegation.api_mode`;
- `delegation.reasoning_effort`;
- `delegation.max_iterations`;
- `delegation.child_timeout_seconds`;
- `delegation.max_concurrent_children`;
- `delegation.max_spawn_depth`.

Vesta should borrow this instead of inventing a separate model-router surface in
v0. A run may declare a worker lane in `run.md`, and each
`worker_state` entry should record:

- parent model/provider;
- worker model/provider/base URL class, without secrets;
- assigned objective;
- output contract;
- artifact paths;
- status/failure;
- reason for delegation;
- cache rationale when relevant.

This is important for local llama.cpp-style use. A dense main model can keep a
stable prompt/cache while bounded subtasks run in separate child contexts on a
faster adjacent model, such as an MoE worker. The benefit is not only cost; it
also avoids forcing the main model to ingest side-task context and reprocess a
large cached prefix.

v0 should use explicit or config-driven worker routing. The model may call
Hermes `delegate_task` for bounded side tasks, and a run/eval contract may
declare the worker lane, but Vesta should not auto-route every turn between
models. Automatic model routing can come later as a small deterministic policy,
after the ledger can show which workers were spawned, why, on which model, and
what they produced.

## Prompt Cache Constraint

Ledger behavior should be encouraged by stable, resident runtime instructions,
not intermittent prompt injections. The cached prompt prefix should stay as
stable as possible.

Recommended v0 mechanics:

- one small resident "ledger protocol" in the system/runtime prompt;
- stable tool descriptions for ledger/read/write behavior;
- no mid-session add/remove of ledger tools or ledger instructions;
- dynamic state kept in `ledger.md`, not injected into every turn;
- compaction/resume injects only a short stable-shaped resume packet with paths
  and next action;
- warnings/nudges should be rare and late in the prompt, not early-prefix churn.

Do not implement periodic soft reminders in v0. "Soft" ledger behavior means
resident static instructions and stable tool descriptions, not dynamic nudges
every few turns. Dynamic prompts risk breaking llama.cpp prompt-cache similarity
and forcing expensive full reprocessing.

Hard enforcement should happen only at stable boundaries:

- before compaction;
- before final response;
- after explicit user decision;
- after artifact write;
- after failed command/test;
- after worker completion/failure;
- when finalization sees unresolved contradictions;
- when finalization sees unsupported high-materiality claims.

When a hard gate finds missing ledger state, it should request a repair turn
first. The model appends the required entry via `ledger_append`, then continues.
Only block if the repair turn fails. Do not silently auto-append semantic ledger
entries in runtime code; the model owns the meaning.

Gate bands:

1. Core flow: compaction, final response, explicit user decision, artifact write.
2. Quality/failure flow: failed command/test, worker completion/failure,
   unresolved contradictions, unsupported high-materiality claims.

Artifact gates apply to declared durable outputs, not every file edit. Vesta is
not only a coding agent; artifacts are outputs a human may later rely on. A
source-code edit is an artifact only when the run declares it as a deliverable
or records it as part of a patch/diff/result package.

Declared artifacts use hybrid ownership:

- runtime declares artifacts from commitments, output contracts, and known run
  paths;
- the model declares semantic artifacts through `ledger_append`;
- explicit user requests override both;
- runtime may mechanically register raw payloads, logs, and tool outputs, but
  should not invent semantic artifact meaning without a path contract,
  commitment, or model/user declaration.

Normal chat answers are not automatically artifacts. An output becomes expected
only through a contract: user request, model commitment, worker output contract,
or known run path.

## Minimal v0 Storage

Start with files:

- `ledger.md`;
- `raw/` for full source/tool payloads;
- `artifact-manifest.md` or `artifact-manifest.json`;
- `resume-packet.md`;
- optional generated indexes later.

The v0 model should privilege strict invariants over schema completeness.

## Finalization Rule

Vesta should not finish from memory of activity. It should finish from recorded
state, with bounded trust rather than maximal suspicion.

- high-materiality factual claims have evidence, are labeled as hypotheses, or
  are explicitly accepted with low confidence;
- expected artifacts exist or are marked missing;
- contradictions are resolved or explicitly blocking;
- worker failures/truncation are visible;
- verification ran or has a skip reason;
- next action is clear when work remains.

The evidence rule is not "prove every sentence." Low-risk interpretation,
planning judgment, ideation, prioritization, and ordinary model synthesis may
stand without source-grade evidence when they are clearly not material factual
claims. The runtime should prevent unsupported important claims, not turn every
session into an endless research loop.

For non-coding work, finalization is domain-neutral: check objective,
commitments, artifacts, material claims, gaps, contradictions, worker state, and
next action. Tests, diffs, and validators are required only when the task
touches code, configuration, or risky operational behavior.

## Repair UX

Repair gates should be model-facing first. A failed broad read, missing ledger
entry, or missing finalization fact should return a short tool/gate error that
tells the model how to repair the state. The UI may show a compact activity
note, but should not interrupt the user unless a repair fails repeatedly or a
real human preference is needed.

## Worker Acceptance

The parent agent should not accept delegated work from a summary alone. Worker
acceptance requires:

- a `worker_state` entry;
- output refs or artifacts;
- declared gaps/failures;
- a spot audit for high-materiality claims.

This keeps worker orchestration inspectable and prevents silent delegation
failure from looking like completed work.

## Raw Retention And Privacy

Raw outputs are retained locally inside the run by default because auditability
is a product feature. Vesta should provide cleanup/purge controls and later TTL
configuration. Model-facing excerpts should be redacted where appropriate; raw
payloads may remain unredacted as audit material, but this must be visible and
controllable.

## Non-Code Workspace Semantics

Workspace is not always a Git repository. For document, research, planning,
ideation, or reflective runs, workspace means the current project/domain/person
context. These runs still receive the same primitives: `run_id`, `run.md`,
`ledger.md`, `raw/`, artifact manifest, and finalization state.

## Validator Boundary

Selective validation is a v0 contract, not a full v0 engine. The runtime should
record when validation is expected and run cheap deterministic or high-risk
checks where available. A full validator engine belongs after the ledger/eval
foundation is proven.
