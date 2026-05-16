# Vesta Runtime User Stories

Date: 2026-05-16
Status: Evidence-backed story set for implementation planning

This file turns the completed Vesta design phase and the broader Hermes/local
agent research corpus into user-need stories. It does not create
implementation tasks.

## Evidence Map

- **E1 - Product/design decisions:** `VESTA_PRODUCT_IDEA.md`,
  `VESTA_DESIGN_INTERVIEW.md`, `VESTA_LEDGER_DESIGN.md`, and
  `work/vesta-runtime/prd.md` establish the accepted direction: local/private
  runtime, Markdown ledger, run substrate, retrieval discipline,
  compaction/resume, finalization, workers, raw refs, and v0 boundaries.
- **E2 - Hermes live benchmark failure modes:** `observer-evaluation.md` and
  `hermes-tuning-notes.md` show repeated compactions, `Active Task: None` risk,
  large read/compact loops, missing worker artifacts, flawed high-impact claims
  such as license/default-threshold drift, and need for final evidence audit.
- **E3 - Local coding benchmark signals:** `suite-20260513.md`,
  `task-plan.md`, `inventory.md`, and `validator-tool-design.md` show copied
  corpus discipline, exact prompt/diff/test capture, prompt-cache latency
  cliffs, passing tests hiding semantic drift, and selective validator need.
- **E4 - Hermes capability research:** `harness-research` Hermes reports show
  Hermes has strong personal-agent surfaces: sessions, tools, plugins,
  delegation, memory/search, profile-aware paths, local endpoints, and
  extension hooks, but is single-operator and not an enterprise isolation
  boundary.
- **E5 - Comparative harness research:** comparison/Pi/Kilo/OpenHands/Claude
  reports show adjacent patterns: Pi as hackable substrate, Kilo as stronger
  product/IDE UX, OpenHands as workplace/sandbox/control-plane candidate, and
  Claude Code as architecture reference for permissions/session recovery.
- **E6 - AionUi audit:** AionUi is a credible ACP/local GUI/control-plane
  candidate and can expose lifecycle/context/process state, but does not fix
  Hermes retrieval, compaction, evidence-ledger, or harness semantics by itself.
- **E7 - User/work-style profile:** `profile.md` shows strong local-first,
  evidence-first, inspectable-model, SQLite/FTS/local-model, bounded retrieval,
  audit/logging, and operator-oriented preferences across Damyan's projects.
- **E8 - Hermes source surface audit:**
  `work/vesta-runtime/hermes-surface-overlap.md` maps each story to existing
  or partial Hermes surfaces so implementation can reuse before rebuilding.

Signal strength in stories:

- **Strong:** directly supported by accepted design decisions and multiple
  research artifacts or live observations.
- **Medium:** supported by accepted direction plus one strong research signal,
  but exact UX/details remain open.
- **Weak:** plausible from research, but not yet enough evidence to make it a
  committed v0 capability.

Hermes overlap marker:

- **Reuse:** use an existing Hermes primitive directly or through a thin Vesta
  wrapper.
- **Extend:** Hermes has the adjacent primitive; Vesta adds run/ledger/artifact
  semantics.
- **Build:** no meaningful Hermes surface found; Vesta owns the product
  primitive.

## 1. Core User Stories

### C01 - Durable Run Identity

As a local user, I want Vesta to wrap Hermes session lineage in a stable run
identity so that I can inspect and resume the work even if Hermes rotates
session IDs during compaction.

- Evidence: Strong. E1 accepts `run_id` separate from `session_id`; E2 observed
  multiple compression continuation sessions; E4 confirms Hermes session
  lineage exists and can be reused; E8 confirms `parent_session_id` chains.
- Hermes overlap: Extend. Reuse Hermes `session_id` and `parent_session_id`;
  add stable Vesta `run_id` above them.
- Acceptance notes: A completed run has a stable `run_id`, records current and
  prior Hermes session IDs, and keeps artifacts under one run directory.

### C02 - Eager Run Files

As a local user, I want Vesta to create `run.md` and `ledger.md` at session
start so that compaction, artifacts, workers, and finalization never depend on
lazy state creation.

- Evidence: Strong. E1 explicitly accepts eager seed files; E2 shows late
  compaction and artifact-pressure failures where missing state is dangerous;
  E8 confirms Hermes has session logs but no eager Vesta run files.
- Hermes overlap: Build. Use profile-aware storage conventions, not Hermes
  transcript/session logs, as the model-facing run surface.
- Acceptance notes: Empty or near-empty files exist before the first material
  task.

### C03 - Operational Ledger

As a local user, I want a durable Markdown ledger that records what is known,
decided, missing, promised, produced, and next so that transcript prose is not
the runtime's source of truth.

- Evidence: Strong. E1 defines ledger as durable epistemic, operational, and
  artifact state; E2 shows prose compaction can lose task pressure; E8 confirms
  Hermes memory/session search is not a run ledger.
- Hermes overlap: Build. Hermes transcript, memory, and session search remain
  inputs; Vesta ledger is the authoritative runtime state.
- Acceptance notes: Ledger records claims, decisions, gaps, contradictions,
  commitments, artifacts, workers, checkpoints, and next action.

### C04 - Model-Friendly Markdown Memory

As a local user, I want the model-facing ledger to be Markdown rather than
JSONL/SQL so that the model can consume it reliably and I can inspect it
quickly.

- Evidence: Strong. E1 accepts Markdown-first; design discussion rejected
  model-authored JSONL/SQLite as unnecessary failure modes; E8 finds no Hermes
  Markdown runtime ledger surface.
- Hermes overlap: Build. SQLite/session storage can index or support later, but
  `ledger.md` is the primary model-read surface.
- Acceptance notes: Structured indexes may exist later, but the primary
  model-read surface is `ledger.md`.

### C05 - Runtime-Owned Time

As a local user, I want all run, ledger, source, artifact, worker, checkpoint,
and finalization timestamps to come from the runtime so that chronology is not
corrupted by model guesses.

- Evidence: Strong. E1 accepts runtime-owned timestamps and reuse of
  `hermes_time.py`; user explicitly called out timestamp consistency; E8
  confirms the reusable clock primitive.
- Hermes overlap: Reuse. Vesta should standardize on `hermes_time.now()` and
  avoid model-authored timestamps.
- Acceptance notes: Model never authors timestamp values directly.

### C06 - Material Action Ledger Writes

As a local user, I want the model to append ledger entries after material
actions so that important progress is preserved before compaction or context
loss.

- Evidence: Strong. E1 accepts continuous ledger updates; E2 shows long-running
  workers collecting evidence across many compactions; E8 identifies existing
  post-tool/lifecycle hooks as possible enforcement points.
- Hermes overlap: Extend. Add Vesta ledger policy on top of Hermes tool and
  lifecycle hooks where possible.
- Acceptance notes: Trivial mechanics do not need entries; material claims,
  decisions, artifacts, gaps, failures, worker updates, and next actions do.

### C07 - Dedicated Ledger Append

As a local user, I want normal ledger writes to go through a dedicated append
primitive so that the model does not patch or rewrite the whole ledger.

- Evidence: Strong. E1 accepts `ledger_append`; design rejected direct
  whole-ledger patching due to fragility; E8 confirms Hermes can register tools
  and plugin tools without rebuilding the tool substrate.
- Hermes overlap: Extend. Register a Vesta append primitive through Hermes'
  tool/plugin surface; do not hand-edit the full ledger.
- Acceptance notes: Runtime supplies id, timestamp, actor, run/session metadata.

### C08 - Raw Evidence Outside Context

As a local user, I want Vesta to turn Hermes' large-output spill behavior into
run-scoped raw evidence so that the model receives useful excerpts and refs
without flooding local context.

- Evidence: Strong. E1 and E4 show Hermes has tool-result spill mechanics; E2
  and E3 show tool output dominates context in long runs; E8 confirms current
  spill is temp/sandbox-oriented rather than run-owned.
- Hermes overlap: Extend. Reuse output caps/spill patterns; store Vesta raw refs
  under the run with locator, excerpt, hash, and retention metadata.
- Acceptance notes: Raw refs include path/locator, excerpt, hash where
  available, and capture metadata.

### C09 - Ledger-Aware Compaction

As a local user, I want Vesta to piggyback on Hermes compression lineage while
checkpointing active runtime state into the ledger so that a resumed model keeps
task pressure and next action.

- Evidence: Strong. E1 accepts compaction/resume contract; E2 observed
  `Active Task: None` despite pending report deliverables; E8 confirms Hermes
  has child sessions and resume tip resolution but no ledger resume packet.
- Hermes overlap: Extend. Reuse Hermes compression child sessions; make Vesta's
  resume packet ledger-derived and run-owned.
- Acceptance notes: Resume packet includes objective, commitments, gaps,
  contradictions, worker state, artifacts, ledger path, and exactly one next
  action when work remains.

### C10 - Finalization From Recorded State

As a local user, I want Vesta to finalize from ledger/artifact/verification
state rather than memory of activity so that confident but unsupported endings
are blocked or qualified.

- Evidence: Strong. E1 accepts bounded-trust finalization; E2 reports flawed
  high-impact claims; E3 shows tests can pass while semantic drift remains; E8
  finds no existing finalization gate from durable run state.
- Hermes overlap: Build/Extend. Use lifecycle/finalize hooks if sufficient, but
  Vesta owns the finalization packet and blocking rules.
- Acceptance notes: Final answer reflects unresolved contradictions, missing
  artifacts, failed workers, skipped verification, and residual risk.

### C11 - Evidence For High-Materiality Claims

As a local user, I want high-materiality claims to have evidence or explicit
uncertainty so that reports and recommendations can be audited.

- Evidence: Strong. E1 accepts materiality-based evidence; E2 observed license
  and compression-threshold claims that needed source cross-checking; E8 finds
  no existing materiality/evidence gate.
- Hermes overlap: Build. This is Vesta ledger/finalization policy, not current
  Hermes runtime behavior.
- Acceptance notes: Unsupported important claims are labeled, deferred, or
  blocked from finalization.

### C12 - Artifact Commitments

As a local user, I want promised outputs to become tracked artifacts so that
reports, plans, patches, handoffs, and saved syntheses cannot disappear
silently.

- Evidence: Strong. E1 accepts hybrid artifact ownership; E2 observed missing
  `reports/pi.md` and parent orchestration uncertainty; E8 confirms Hermes
  stores sessions/trajectories but not artifact commitments.
- Hermes overlap: Build/Extend. Reuse storage/log paths where useful; Vesta adds
  artifact manifest and commitment pressure.
- Acceptance notes: Expected artifacts come from user request, model
  commitment, worker contract, or known run path.

### C13 - Non-Code First-Class Runs

As a local user, I want research, planning, ideation, document analysis, and
reflective discussion to use the same run/ledger/artifact primitives as code
work so that Vesta is not just a coding harness.

- Evidence: Strong. E1 explicitly says Vesta is broader than a coding agent;
  E7 shows local-first research, memory, teaching, and operator workflows; E8
  confirms Hermes has broad assistant surfaces but no domain-neutral run
  substrate.
- Hermes overlap: Build. The same Vesta run substrate applies across domains;
  code-specific Hermes affordances remain optional.
- Acceptance notes: Non-code finalization does not require tests/diffs unless
  the task involves code or operational risk.

### C14 - Locator-First Retrieval By Default

As a local user, I want Vesta to enforce locator-first retrieval through Hermes'
existing search/read tools so that local models do not waste time and prompt
cache on unnecessary full-file ingestion.

- Evidence: Strong. E1 accepts retrieval discipline; E2 observed read/compact
  loops; E3 observed prompt-cache latency cliffs from long retrieval sessions;
  E8 confirms `search_files`, `read_file(offset, limit)`, read dedup, and output
  caps already exist.
- Hermes overlap: Extend. Reuse `search_files`/`read_file`; add Vesta
  locator-history, repair, and ledger-ref policy.
- Acceptance notes: Normal source work uses manifests/search/counts and narrow
  windows before broad reads.

### C15 - Complete-Coverage Document Reading

As a local user, I want the agent to read whole documents when the task truly
requires complete coverage so that summaries and explanations are not limited
to search hits.

- Evidence: Strong. E1 accepts whole-document path; user explicitly gave long
  scientific papers as a use case while warning against overfitting; E8 confirms
  Hermes has file pagination but no complete-coverage document workflow.
- Hermes overlap: Build on tools. Use existing reads/output limits, but Vesta
  owns intent detection, coverage state, and threshold behavior.
- Acceptance notes: Complete coverage is deliberate; it is not the default
  retrieval move.

### C16 - Chunk/Ledger Long-Document Understanding

As a local user, I want large documents to be chunked and summarized into the
ledger with raw refs so that the final synthesis can cover the whole artifact
without losing exact details.

- Evidence: Strong. E1 accepts chunk/ledger workflow; long-context research
  reviewed during design supports chunked summarization with targeted rereads;
  E8 finds no Hermes chunk-to-ledger document reader.
- Hermes overlap: Build on tools. Use paginated file reads; add Vesta chunk
  summaries and raw/source refs.
- Acceptance notes: Chunk findings include source refs and gaps; high-impact
  details can reread the smallest raw range.

### C17 - Prior-Chunk Recap Context

As a local user, I want later chunks of a long document to be read with compact
recaps of earlier chunks so that sections depending on earlier definitions,
methods, or arguments are not misinterpreted in isolation.

- Evidence: Strong. E1 now accepts whole-document chunks carrying prior recap
  context; user explicitly raised scientific papers where chunk 4 depends on
  chunks 1-3; E8 finds no existing rolling recap surface.
- Hermes overlap: Build. This is a Vesta whole-document workflow layered over
  the existing read primitives.
- Acceptance notes: Chunk N receives document objective, document map when
  available, prior recap, unresolved terms/questions, and current chunk raw
  text. Raw prior chunks are not reinjected by default; recaps collapse
  hierarchically if they grow too large.

### C18 - User-Controlled Retrieval Strictness

As a local user, I want Vesta retrieval strictness exposed through Hermes-style
config or CLI so that I can trade context economy for speed when the gate costs
more than a broad read.

- Evidence: Strong. E1 accepts two-state strictness and rejects v0 `off`; user
  explicitly requested the behavior be exposed rather than hidden; E8 confirms
  config/CLI plumbing already exists for adjacent knobs.
- Hermes overlap: Extend. Add Vesta config keys first; UI can follow without
  changing the runtime contract.
- Acceptance notes: Default is `disciplined`; `permissive` reduces repair
  friction while preserving ledger/raw refs.

### C19 - Configurable Whole-Document Thresholds

As a local user, I want whole-document thresholds to be configurable so that the
runtime matches my hardware, context window, and current task.

- Evidence: Strong. E1 accepts user-controllable thresholds; E3 shows local
  context and prompt-cache behavior materially affect runtime latency; E8
  confirms existing `tool_output`/`file_read_max_chars` knobs but no Vesta
  whole-document thresholds.
- Hermes overlap: Extend. Place whole-document thresholds beside existing
  Hermes config/output-limit settings.
- Acceptance notes: Until UI exists, config or CLI exposure is acceptable and
  missing UI is documented product debt.

### C20 - Worker State And Parent Acceptance

As a local user, I want Vesta to wrap Hermes `delegate_task` workers with
durable state, outputs, failures, gaps, and high-materiality claims so that the
parent can accept work deliberately rather than trusting polished summaries.

- Evidence: Strong. E1 accepts worker acceptance rules; E2 observed missing
  worker artifacts and flawed worker report claims; original task warned not to
  treat worker prose as authority; E8 confirms Hermes has strong transient
  delegation but no durable worker manifest.
- Hermes overlap: Extend. Reuse `delegate_task` and delegation limits; add
  Vesta `worker_state`, artifact contracts, and acceptance gates.
- Acceptance notes: Parent acceptance requires `worker_state`, output refs or
  artifacts, declared gaps/failures, and spot audit for material claims.

### C21 - Adjacent Worker Model Lane

As a local user, I want bounded worker tasks to reuse Hermes delegation model
configuration when useful so that the main dense model preserves prompt cache
and workers can use faster local capacity.

- Evidence: Strong. E1 accepts Hermes `delegation.*` reuse and adjacent model
  lane; E3 validator notes propose fast MoE side model; user explicitly raised
  separate contexts to avoid main-model cache reprocessing; E8 confirms worker
  model/provider/base URL overrides already exist.
- Hermes overlap: Reuse/Extend. Use Hermes `delegation.*` as the v0 lane; add
  Vesta run metadata and keep routing explicit.
- Acceptance notes: v0 routing is explicit/config-driven, not autonomous
  per-turn routing.

## 2. Supporting User Stories

### S01 - Copied-Repo Coding Runs

As a local user, I want coding evals to reuse Hermes worktree/checkpoint
surfaces where useful while preserving copied-repo run discipline so that
experiments do not mutate my original projects.

- Evidence: Strong. E1 and E3 accept copied corpus/run directories; benchmark
  inventory and task plan emphasize sanitized copies; E8 confirms Hermes has
  `--worktree` and filesystem checkpoints, but not eval copied-corpus capture.
- Hermes overlap: Extend. Consider `--worktree` and checkpoints as safety
  primitives; Vesta still records original/copy workspace pair.
- Acceptance notes: Run captures original source path and copied workspace path.

### S02 - Prompt/Config/Model Capture

As a local user, I want each run to preserve prompt, model, provider, context,
runtime config, and endpoint metadata so that I can understand and compare
results later.

- Evidence: Strong. E1 includes prompt/config/model capture; E3 benchmark
  protocol records prompt, slots, context, temperature, tokens, and outputs; E8
  confirms Hermes sessions already store some prompt/model metadata.
- Hermes overlap: Extend. Reuse available session metadata; Vesta writes a
  run-level manifest that excludes secrets.
- Acceptance notes: Secrets are not stored in plain run metadata.

### S03 - Verification Capture

As a local user, I want tests/builds/static checks and their outputs captured so
that a final verdict is tied to what was actually verified.

- Evidence: Strong. E1 includes verification/finalization; E3 benchmark tasks
  require exact command outputs and independent post-run checks; E8 confirms
  Hermes has tool transcripts/output spill but not verification state.
- Hermes overlap: Build/Extend. Capture verification as Vesta state rather than
  relying on transcript text alone.
- Acceptance notes: Skipped verification requires an explicit skip reason.

### S04 - Failed Commands As State

As a local user, I want failed commands, missing paths, and recovery actions
recorded as state so that failures are not hidden in narrative.

- Evidence: Strong. E1 treats failure as ledger state; E2 observed useful
  missing-path recovery and recommends failure as state; E8 confirms Hermes
  captures tool failures but does not promote material failures into run state.
- Hermes overlap: Build/Extend. Reuse tool result data; materialize failures in
  ledger/finalization.
- Acceptance notes: Repeated or material failures can affect finalization.

### S05 - Negative Evidence

As a local user, I want zero-match searches and wrong path guesses recorded when
they matter so that the agent does not rediscover the same dead end.

- Evidence: Medium. E1 and tuning notes support negative evidence; E2 observed
  file-not-found recovery as signal; E8 confirms search tools expose zero-match
  outcomes but do not persist them as evidence.
- Hermes overlap: Build/Extend. Promote only material negative evidence from
  search/tool outputs into the ledger.
- Acceptance notes: Only material negative evidence is recorded to avoid noise.

### S06 - Bounded Trust For Synthesis

As a local user, I want the runtime to distinguish high-materiality claims from
low-risk judgment so that practical work does not become endless evidence
collection.

- Evidence: Strong. E1 accepts bounded trust; user explicitly rejected
  "evidence or die" behavior; E8 finds no existing Hermes materiality model.
- Hermes overlap: Build. This belongs to Vesta ledger/finalization policy.
- Acceptance notes: Low-risk interpretation can stand when clearly not a
  material factual claim.

### S07 - Domain-Neutral Artifacts

As a local user, I want artifact tracking to cover reports, plans, prompts,
handoffs, generated documents, eval results, and patches so that non-code work
is not second-class.

- Evidence: Strong. E1 defines artifacts beyond code; E7 shows document,
  teaching, research, and local product workflows; E8 confirms Hermes sessions
  and trajectories are not artifact commitments.
- Hermes overlap: Build/Extend. Reuse storage conventions; Vesta owns artifact
  contract and manifest semantics.
- Acceptance notes: Normal chat remains non-artifact unless a contract exists.

### S08 - Domain-Neutral Finalization

As a local user, I want finalization rules to apply to research/planning without
forcing code-specific tests so that non-code outputs can still be accountable.

- Evidence: Strong. E1 finalization decision; E7 evidence-first non-code
  projects; E8 finds no domain-neutral finalization gate.
- Hermes overlap: Build. Vesta finalization is domain-neutral and ledger-based.
- Acceptance notes: Check objective, commitments, artifacts, material claims,
  gaps, contradictions, worker state, and next action.

### S09 - Stable Prompt Cache Contract

As a local user, I want Vesta's runtime instructions and tools to stay stable
during a run so that local prompt-cache similarity is not broken by dynamic
nudges.

- Evidence: Strong. E1 accepts stable resident protocol; E3 observed prompt
  cache reprocessing cliffs after long runs; E8 confirms Hermes reuses stored
  prompt/system state on continuations.
- Hermes overlap: Reuse/Extend. Preserve Hermes prompt-cache-friendly behavior;
  put dynamic Vesta state in files.
- Acceptance notes: Dynamic state lives in files; runtime policy changes do not
  add/remove tool descriptions or system instructions mid-session.

### S10 - Repair-First Gates

As a local user, I want gates to let the model repair missing state before
blocking so that runtime discipline does not become a constant user
interruption.

- Evidence: Strong. E1 accepts repair-first gates; user accepted model-facing
  repair UX; E8 confirms pre-tool hooks can block/repair tool calls.
- Hermes overlap: Extend. Implement stateful Vesta gates on top of existing
  pre-tool/blocking surfaces where possible.
- Acceptance notes: User sees explicit choice only after repeated repair
  failure or real human preference need.

### S11 - Broad-Read Repair Without Drama

As a local user, I want broad-read gates to ask the model to narrow or justify
only when needed so that ordinary work stays fast.

- Evidence: Strong. E1 accepts exact gate semantics; user agreed to
  repair-first behavior and UI-exposed strictness; E8 confirms file reads,
  search tools, and pre-tool hooks already exist.
- Hermes overlap: Extend. Reuse existing tools; add Vesta locator-history and
  justification checks.
- Acceptance notes: In `disciplined`, gate repairs only if locator history,
  complete-coverage need, and escalation reason are all absent.

### S12 - Raw Retention Controls

As a local user, I want raw outputs retained locally by default but purgeable so
that auditability does not turn into uncontrolled storage growth.

- Evidence: Strong. E1 accepts local raw retention with cleanup/TTL future; E7
  strongly supports local/private and auditability; E8 confirms redaction/spill
  exists but not run-scoped purge state.
- Hermes overlap: Extend. Reuse redaction/output-spill primitives; add raw
  retention manifest and purge semantics under Vesta.
- Acceptance notes: Raw payloads can be unredacted audit material, but visibility
  and controls are required.

### S13 - Profile-Aware Storage

As a local user, I want Vesta state to follow Hermes profile-aware paths so that
different Hermes profiles do not leak state into each other.

- Evidence: Strong. E1 accepts `get_hermes_home()`; E4 shows Hermes uses
  profile-aware state/log paths; E8 confirms this is a reusable primitive.
- Hermes overlap: Reuse. Vesta state belongs under the active Hermes home/profile.
- Acceptance notes: User-facing path display uses profile-aware helpers.

### S14 - Small Plugin-First Extension

As a local user who will maintain the fork, I want Vesta to use Hermes plugin
and hook surfaces where possible so that upstream alignment remains practical.

- Evidence: Strong. E1 accepts plugin-first/minimal core hooks; E4 documents
  Hermes extension surfaces; E8 confirms tool, transform, shell, and lifecycle
  hooks already exist.
- Hermes overlap: Reuse/Extend. Prefer Hermes plugin/hook seams; add narrow core
  hooks only when lifecycle boundaries are missing.
- Acceptance notes: Core patches are narrow lifecycle hooks where plugin hooks
  cannot enforce required behavior.

### S15 - Selective Validator Contract

As a local user, I want high-risk patches to have an optional skeptical
validator pass so that passing tests are not treated as enough for merge
readiness.

- Evidence: Strong. E1 accepts validator as v0 contract; E3 shows passing tests
  hid behavior-preservation issue and defines validator trigger candidates; E8
  finds no existing skeptical validator lane.
- Hermes overlap: Build/Extend. Define the Vesta contract now; execution can
  later reuse delegation or auxiliary model surfaces.
- Acceptance notes: Validator is selective and decision-oriented, not always-on
  or a second full coding session.

### S16 - Validator Separation

As a local user, I want validator findings reported separately from primary
model score so that I can distinguish model capability from harness-assisted
quality control.

- Evidence: Medium. E3 validator design explicitly recommends separate scoring;
  E1 accepts validator contract but not full engine; E8 confirms Hermes does not
  separate validator results today.
- Hermes overlap: Build. Vesta owns the reporting separation.
- Acceptance notes: Report identifies what the primary did, what tests caught,
  and what validator caught.

### S17 - AionUi As Control-Plane Candidate

As a local user, I want Vesta to be testable behind existing Hermes ACP/TUI
control surfaces so that I can later get lifecycle and session visibility
without making UI the core product.

- Evidence: Medium. E1 positions AionUi as control-plane test client; E6 finds
  AionUi credible but not a harness replacement; E8 confirms Hermes has ACP,
  TUI, dashboard PTY, and spawn-tree visibility surfaces.
- Hermes overlap: Extend. Use existing ACP/TUI paths for bounded tests; Vesta
  artifacts remain authoritative.
- Acceptance notes: Local-only bounded test before remote/WebUI use.

### S18 - Process/Session Visibility

As a local user, I want process, stderr, exit, context usage, and session state
visible enough for postmortem so that UI wrappers do not hide harness failures.

- Evidence: Medium. E6 shows AionUi's lifecycle visibility is valuable and warns
  GUI may hide failures; E2 observer interruption killed a benchmark process;
  E8 confirms TUI/ACP/session/process visibility already exists.
- Hermes overlap: Extend. Read or expose Hermes process/session signals through
  Vesta run artifacts rather than inferring truth from UI state.
- Acceptance notes: This may be surfaced through Vesta artifacts first, UI
  later.

### S19 - Exact Source Locators

As a local user, I want claims to cite source paths, line ranges, commands, or
raw output refs so that I can verify important conclusions quickly.

- Evidence: Strong. E1 source refs; E2 observer measured evidence discipline and
  found unsupported claims; E7 evidence-first preference; E8 confirms line
  numbered file reads and raw refs exist partially.
- Hermes overlap: Extend. Reuse line-window reads and raw refs; add Vesta
  source-ref rows in Markdown.
- Acceptance notes: Material claims link to evidence or are labeled uncertain.

### S20 - Newest Instruction Wins

As a local user, I want Vesta to preserve the latest user direction after
interruption, resume, or context transition so that old summaries do not steer
the run.

- Evidence: Medium. E2 tuning notes emphasize newest instruction after resume;
  current design process had interruption/compaction concerns; E8 confirms
  Hermes resume/session search exists but is not ledger-authoritative.
- Hermes overlap: Extend. Vesta ledger next action and resume packet become the
  authoritative continuation state.
- Acceptance notes: Resume packet and ledger next action should reflect current
  active instruction.

## 3. Edge-Case User Stories

### E01 - Resume After Many Compactions

As a local user, I want Vesta to preserve task pressure after multiple
compactions so that long research does not drift into endless collection.

- Evidence: Strong. E2 observed five-plus compactions and read/compact loops.
- Hermes overlap: Extend. Hermes creates compression-linked child sessions;
  Vesta adds ledger pressure, stop conditions, and synthesis triggers.
- Acceptance notes: After configured compaction/read thresholds, worker should
  synthesize known facts and gaps instead of collecting indefinitely.

### E02 - Incomplete Worker Artifact

As a local user, I want missing worker deliverables to block silent success so
that a parent cannot report full coverage when a worker never produced its
artifact.

- Evidence: Strong. E2 observed Pi worker never produced report before process
  termination; original task expected reports per worker; E8 confirms Hermes
  workers are transient and do not have durable artifact acceptance.
- Hermes overlap: Extend. Reuse worker spawning; Vesta finalization checks
  expected worker artifacts.
- Acceptance notes: Finalization lists missing artifacts and impact.

### E03 - Worker Truncation Or Spawn Limit

As a local user, I want Vesta to record requested, accepted, truncated, failed,
and completed workers so that orchestration limits do not masquerade as
completed work.

- Evidence: Strong. E2 observed excess delegate tasks truncated by concurrency
  limit and parent coverage uncertainty; E8 confirms Hermes caps/truncates
  delegation but does not persist a Vesta worker manifest.
- Hermes overlap: Extend. Capture requested, accepted, truncated, failed, and
  completed worker counts from delegation state.
- Acceptance notes: Worker manifest distinguishes requested vs accepted.

### E04 - Wrong But Polished Worker Report

As a local user, I want high-impact worker claims audited even when prose looks
good so that confident reports do not override source truth.

- Evidence: Strong. E2 observed polished Hermes report with wrong license and
  threshold claims; original task warned worker reports are leads, not
  authority; E8 finds no runtime-enforced worker claim audit.
- Hermes overlap: Build/Extend. Reuse worker outputs as leads; Vesta audits
  high-materiality claims before parent acceptance.
- Acceptance notes: High-materiality claims require source cross-check.

### E05 - Whole-File Temptation In Coding

As a local user, I want the agent discouraged from reading whole source files
for targeted code edits so that local context and prompt cache are preserved.

- Evidence: Strong. E1 retrieval discipline; E2 and E3 show tool output and
  retrieval sessions can dominate context; E8 confirms Hermes already supports
  file search, narrow reads, and dedup warnings.
- Hermes overlap: Extend. Build the preference/gate over existing read/search
  tools.
- Acceptance notes: Full file still allowed with complete-coverage reason or
  permissive policy.

### E06 - Whole-Document Need In Research

As a local user, I want the agent allowed to consume whole long papers or
reports when I ask for global understanding so that locator-first discipline
does not cripple document analysis.

- Evidence: Strong. E1 complete-coverage path and user-provided paper example.
- Hermes overlap: Build on tools. Hermes can page through files; Vesta owns
  whole-document coverage, chunking, and rolling recaps.
- Acceptance notes: Large docs use chunk/ledger workflow and preserve raw refs.

### E07 - Post-Compact Reread Suppression

As a local user, I want Vesta to consult the ledger before rereading sources
after compaction so that it does not rehydrate large context unnecessarily.

- Evidence: Strong. E1 compaction/retrieval decisions; E2 read/compact loop.
- Hermes overlap: Extend. Hermes resets some read-dedup state after compression;
  Vesta ledger/raw refs suppress unnecessary rereads.
- Acceptance notes: Reread only smallest range needed for high-materiality
  verification or insufficient prior evidence.

### E08 - Prompt Cache Cliff

As a local user, I want Vesta to avoid avoidable prompt-cache reprocessing so
that local runs do not incur large latency cliffs unrelated to reasoning.

- Evidence: Strong. E3 observed full reprocessing around 108k tokens after
  summary request despite recent cache; E1 prompt-cache stability; E8 confirms
  Hermes has prompt-cache-friendly continuation behavior to preserve.
- Hermes overlap: Reuse/Extend. Keep Hermes stable prompt/tool surfaces; put
  changing Vesta state in files and config.
- Acceptance notes: Stable prompt/tool surface and file-backed dynamic state.

### E09 - Incomplete Security Review

As a local user, I want security review outputs to state gaps and residual risk
instead of pretending certainty when iteration budget or retrieval was
insufficient.

- Evidence: Strong. E3 security-review task hit iteration budget but produced
  useful findings with caveats; E1 finalization gap handling; E8 finds no
  existing Vesta-style residual-risk finalization.
- Hermes overlap: Build. This is Vesta finalization behavior.
- Acceptance notes: Finalization can mark useful/accepted with caveats.

### E10 - Failed Observation Process

As a local user, I want process interruption or lost PTY events to be visible in
the run state so that benchmark failure is not misattributed to the model.

- Evidence: Medium. E2 observer interruption terminated live Hermes benchmark;
  E6 AionUi audit values lifecycle/process supervision; E8 confirms Hermes
  exposes session/process/UI signals but not run-level failure taxonomy.
- Hermes overlap: Extend. Promote interruption/end reason into Vesta run state.
- Acceptance notes: Final run records interruption/end reason where available.

### E11 - Sensitive Local Data Exclusion

As a local user, I want corpus creation and run capture to avoid private DBs,
HAR files, audio, envs, and secrets unless explicitly allowed so that local
auditability does not leak sensitive material.

- Evidence: Strong. E3 inventory excludes sensitive paths; original task warned
  against private data files; E7 privacy/local-first pattern; E8 confirms Hermes
  has redaction/checkpoint excludes but not Vesta capture policy.
- Hermes overlap: Extend. Reuse redaction/exclude primitives; add run/corpus
  allow/deny manifest.
- Acceptance notes: Exclusion rules are visible and overridable only
  deliberately.

### E12 - Permissive Read Still Auditable

As a local user, I want permissive mode to reduce friction without losing audit
refs so that speed mode does not become invisible mode.

- Evidence: Strong. E1 accepts permissive without `off`.
- Hermes overlap: Extend. Same Hermes read/search/output tools; Vesta changes
  strictness policy while retaining audit refs.
- Acceptance notes: Broad reads in permissive still record lightweight reason
  and raw refs.

## 4. Admin / Operator Stories

### O01 - Inspect A Run Directory

As an operator of my local agent runtime, I want to open a run directory and see
metadata, ledger, raw outputs, artifacts, resume packet, and finalization so
that I can debug without replaying the chat.

- Evidence: Strong. E1 PRD/storage shape; E3 benchmark run output layout; E7
  operator-oriented evidence/log preferences; E8 confirms Hermes has session
  logs, trajectories, TUI snapshots, and raw spills but not Vesta run dirs.
- Hermes overlap: Extend. Surface Hermes-derived state inside a Vesta run
  directory; the run directory is the operator's primary object.
- Acceptance notes: Human-readable files sit beside raw payloads.

### O02 - Configure Retrieval Policy

As an operator, I want to set retrieval strictness and whole-document thresholds
through config or CLI until UI exists so that runtime behavior matches my
hardware.

- Evidence: Strong. E1 accepted config/CLI fallback and UI debt.
- Hermes overlap: Extend. Add Vesta retrieval keys through Hermes config/CLI
  plumbing.
- Acceptance notes: Config values are captured in run metadata.

### O03 - Purge Retained Raw Payloads

As an operator, I want cleanup/purge controls for raw retained data so that
auditability remains compatible with storage and privacy hygiene.

- Evidence: Strong. E1 raw retention/privacy decision; E7 privacy/storage
  preferences; E8 confirms no Vesta-controlled raw purge manifest exists.
- Hermes overlap: Extend. Reuse existing storage/redaction ideas; add purge
  semantics that update refs rather than breaking them.
- Acceptance notes: Purge does not silently corrupt manifests; retained refs
  indicate missing/purged payloads.

### O04 - Preserve Profile Isolation

As an operator, I want Vesta state isolated by Hermes profile so that test,
personal, and future work profiles do not share runtime state accidentally.

- Evidence: Strong. E1 path decision; E4 Hermes profile-aware paths.
- Hermes overlap: Reuse. Use active `get_hermes_home()` profile root.
- Acceptance notes: Uses active Hermes home.

### O05 - Keep Project Repos Clean

As an operator, I want Vesta run state outside project repos by default so that
agent metadata does not pollute working trees.

- Evidence: Strong. E1 run storage under Hermes home; E3 copied corpus and repo
  hygiene concerns; E8 confirms Hermes already has worktree/checkpoint hygiene
  primitives.
- Hermes overlap: Extend. Keep Vesta run state under Hermes home; use explicit
  export for user-requested project artifacts.
- Acceptance notes: Explicit exported artifacts can still be placed in user
  requested paths.

### O06 - See Worker Lane Configuration

As an operator, I want run metadata to show parent and worker model/provider
classes without secrets so that I can understand which local models did what.

- Evidence: Strong. E1 worker lane decision; E3 validator/MoE candidate notes.
- Hermes overlap: Reuse/Extend. Read from Hermes `delegation.*` config and
  Vesta run metadata; omit secrets.
- Acceptance notes: Secrets and API keys are omitted.

### O07 - Separate Primary And Validator Results

As an operator, I want primary agent output, tests, and validator findings
separated so that benchmark results remain interpretable.

- Evidence: Strong. E3 validator-tool design; E1 validator boundary.
- Hermes overlap: Build/Extend. Validator execution may reuse delegation later;
  reporting separation is Vesta-owned.
- Acceptance notes: Validator output is decision-oriented and not mixed into
  primary model score.

### O08 - Run Local-Only Control-Plane Tests

As an operator, I want any AionUi/control-plane experiments to be local-only and
bounded first so that UI convenience does not expand the remote attack surface.

- Evidence: Medium. E6 recommends local-only bounded runtime test and no remote
  until hardening; E1 keeps AionUi as test client; E8 confirms existing ACP/TUI
  surfaces are the nearest integration path.
- Hermes overlap: Extend. Start with Hermes ACP/TUI local surfaces before any
  remote/WebUI assumptions.
- Acceptance notes: Remote/WebUI mode is not assumed safe by default.

### O09 - Audit Prompt Cache And Context Behavior

As an operator, I want runs to capture enough context and prompt-cache metadata
to diagnose latency cliffs on local backends.

- Evidence: Strong. E3 prompt-cache cliff and slot observations; E1 prompt-cache
  constraint; E8 confirms Hermes sessions/config capture some prompt/model
  state already.
- Hermes overlap: Extend. Capture enough Vesta run metadata around Hermes
  prompt/cache behavior without dumping sensitive full prompts by default.
- Acceptance notes: Captured data should be enough for diagnosis without
  dumping sensitive full prompts into every summary.

### O10 - Keep Upstream Alignment Visible

As an operator maintaining the fork, I want Vesta-specific behavior isolated
from upstream Hermes surfaces where possible so that future rebases are
tractable.

- Evidence: Strong. E1 plugin-first/minimal hooks; E4 Hermes extension surfaces.
- Hermes overlap: Reuse/Extend. Keep Vesta deltas visible and justified against
  Hermes hooks, tools, config, ACP/TUI, and storage primitives.
- Acceptance notes: Direct core patches are justified by missing lifecycle
  boundaries.

### O11 - Record Harness Incompleteness

As an operator, I want the run to distinguish model failure, harness failure,
environment failure, and observer interruption so that benchmark conclusions
are honest.

- Evidence: Strong. E2 process termination and E3 harness-incomplete security
  review task; E1 failure as state; E8 confirms Hermes has raw process/session
  signals but no Vesta failure taxonomy.
- Hermes overlap: Extend. Use Hermes signals as input; classify outcome in
  Vesta finalization state.
- Acceptance notes: Finalization can label useful partial evidence without
  declaring success.

### O12 - Export A Handoff

As an operator, I want a clean handoff artifact from a design or research run so
that a next agent can continue implementation planning without reopening
settled product direction.

- Evidence: Strong. E1 design phase status; PRD marks implementation planning
  as next phase; current workflow uses handoff docs; E8 confirms no existing
  Hermes handoff artifact has Vesta's run/ledger contract.
- Hermes overlap: Build/Extend. Reuse session/export material where useful;
  Vesta handoff is ledger-derived.
- Acceptance notes: Handoff references decisions, open questions, and next
  phase boundary.

## 5. Tempting But Not Yet Justified By Evidence

### T01 - Full Enterprise Multi-Tenancy In v0

As a future team user, I might want Vesta to provide multi-tenant isolation,
RBAC, retention policy, and governance from day one.

- Evidence: Weak for v0. E1 explicitly makes v0 personal/local first; E4 says
  Hermes is not an enterprise tenant boundary; E7 supports enterprise thinking
  but not as the first product surface.
- Hermes overlap: None sufficient. Hermes is single-operator/local; do not infer
  enterprise isolation from profile/session separation.
- Why not yet: This should follow a proven local loop.

### T02 - Automatic Per-Turn Model Router

As a local user, I might want Vesta to automatically route every turn between
main, worker, validator, and cheap models.

- Evidence: Weak for v0. E1 explicitly rejects autonomous routing in v0 while
  accepting explicit/config-driven worker lanes; E8 confirms delegation config
  exists for explicit lanes.
- Hermes overlap: Reuse only the explicit `delegation.*` lane, not a router.
- Why not yet: It risks prompt-cache churn and hidden orchestration complexity.

### T03 - User-Facing Task Profiles

As a user, I might want to pick research/coding/planning/ideation profiles at
the start of a run.

- Evidence: Weak for v0. E1 explicitly rejects user-facing profiles; Hermes
  already works as a broad assistant without forcing mode choice.
- Hermes overlap: Avoid copying Hermes profile terminology into user-facing
  task modes; use product defaults and config instead.
- Why not yet: Profiles add UX and routing complexity before the substrate
  proves it needs them.

### T04 - Full Validator Engine In First Build

As a local user, I might want every risky output validated by a complete
second-model review engine immediately.

- Evidence: Medium for need, weak for full v0 scope. E3 strongly supports
  selective validation, but E1 keeps full engine after ledger/eval foundation.
- Hermes overlap: Delegation/auxiliary lanes can run validators later, but the
  v0 story is only the contract.
- Why not yet: The contract belongs in v0; full engine would inflate scope.

### T05 - AionUi As Core Product Surface

As a user, I might want Vesta to begin as a polished GUI/control plane.

- Evidence: Weak for core v0. E6 supports bounded AionUi testing, but E1
  explicitly makes runtime/eval substrate the first surface; E8 confirms Hermes
  already has ACP/TUI surfaces to test before inventing new UI.
- Hermes overlap: Reuse ACP/TUI for experiments; do not make UI authoritative.
- Why not yet: UI could hide weak runtime semantics.

### T06 - Raw Output Cloud Sync

As a future team user, I might want raw run outputs synced to a cloud service
for sharing and analytics.

- Evidence: Weak. E1/E7 emphasize local/private by default; enterprise sharing
  is later.
- Hermes overlap: None sufficient. Existing local storage/redaction does not
  justify cloud sync.
- Why not yet: Privacy, retention, and governance need separate decisions.

### T07 - Semantic Runtime Classifier For Important Outputs

As a user, I might want runtime code to automatically decide which raw outputs
are important evidence.

- Evidence: Weak and counter to accepted direction. E1 explicitly rejects a
  hidden semantic classifier; meaning belongs in ledger/model/user refs.
- Hermes overlap: Avoid. Hermes hooks can enforce explicit policy, but should
  not become an opaque semantic importance classifier.
- Why not yet: It introduces another opaque failure mode.

### T08 - Complete Off Switch For Retrieval Discipline

As a user, I might want to disable retrieval discipline entirely.

- Evidence: Weak for v0. E1 accepts only `disciplined` and `permissive`, no
  `off`.
- Hermes overlap: Existing file tools remain available; Vesta policy should
  still produce raw refs even in permissive mode.
- Why not yet: `permissive` is the escape hatch while preserving auditability.

### T09 - Always-On Validator For Every Patch

As a user, I might want every code change validated by a second model.

- Evidence: Weak for always-on behavior. E3 explicitly says always-on
  validation adds latency and noise; E1 accepts selective triggers.
- Hermes overlap: Delegation can run validators later, but always-on policy is
  intentionally out of scope.
- Why not yet: Use targeted validation for high-risk classes.

### T10 - One Unified Database As Source Of Truth

As a future implementer, I might want to store all Vesta state in SQLite first.

- Evidence: Weak for v0. E1 accepts file-backed Markdown state; SQLite/JSONL may
  be generated indexes later; E8 confirms Hermes already has SQLite transcript
  state, but it is not the Vesta source of truth.
- Hermes overlap: Use Hermes/SQLite as support or index only; keep Markdown
  ledger authoritative for the model.
- Why not yet: Model-authored structured state adds failure modes and reduces
  inspectability.

## Notes For Next Phase

These stories should feed implementation planning and vertical slicing. They
should not reopen the accepted design direction unless a story reveals a direct
contradiction with implementation reality.
