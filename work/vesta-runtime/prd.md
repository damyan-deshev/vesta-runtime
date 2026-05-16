# Vesta Runtime PRD

Date: 2026-05-16
Status: Product design complete; ready for implementation planning

Source decision artifacts:

- `VESTA_PRODUCT_IDEA.md`
- `VESTA_DESIGN_INTERVIEW.md`
- `VESTA_LEDGER_DESIGN.md`

This PRD captures the accepted product direction. It does not create
implementation tasks, slices, or issues.

## 1. Problem Statement

Local agent runs can produce useful coding, research, planning, and synthesis
work, but the harness determines whether the output is trustworthy. Today a run
can appear successful while hiding weak evidence, missing artifacts, lost
compaction state, broad context ingestion, unsupported claims, silent worker
failure, or final answers based on memory rather than durable state.

Vesta Runtime should make long-running local agent work inspectable. A run
should leave durable evidence of what happened, what was known, what was
decided, which artifacts exist, what failed, what remains uncertain, and what
should happen next.

## 2. Target Users

1. Damyan, for local/private coding, research, planning, ideation, and
   reflective work.
2. Senior engineers and platform/infra users working on private codebases with
   local or self-hosted model endpoints.
3. Future small-team or enterprise users who need private agent capacity with
   audit trails, after the personal/local loop is proven.

The v0 product is personal/local first. Enterprise-compatible artifacts should
exist from the beginning, but governance, multi-tenancy, auth, and deployment
are later paths.

## 3. Current Evidence And Research Signals

1. Prior Hermes benchmark and audit research showed the need for durable run
   state, grounded reports, artifact manifests, and better compaction/resume
   behavior.
2. Hermes already provides useful integration anchors: `session_id`,
   `parent_session_id`, `task_id`, session storage, session lineage, tool
   isolation, plugin hooks, tool-result persistence, delegation config, and
   profile-aware storage.
3. Hermes compaction rotates session identity, so Vesta needs a stable `run_id`
   that survives session lineage changes.
4. Hermes has mechanical large tool-result spill behavior. Vesta should
   piggyback on that rather than duplicate raw-output retention.
5. Hermes `read_file` has pagination, character guards, and repeated-read
   dedup/blocking, but file reads still need a broader runtime retrieval
   discipline for local hardware.
6. Hermes has `hermes_time.py`; Vesta should reuse that clock path so models do
   not author timestamps.
7. Hermes delegation config already supports separate worker model/provider
   lanes, which helps keep a dense main model's prompt cache hot while bounded
   work runs elsewhere.
8. Long-context research and practice support the direction: large documents
   should not simply be shoved into context by default, but whole-document
   reading remains valid when the task requires complete coverage.
9. The accepted design phase defines Vesta as broader than a coding agent:
   coding is the first hard eval surface, not the product boundary.

## 4. Product Direction

Vesta Runtime is a local/private agent runtime for auditable long-running work.
It starts from a Hermes fork and initially stays aligned with Hermes where that
reduces risk, but Vesta's product boundary is its own runtime discipline:

- repeatable eval/run harness;
- eager run identity and run directory;
- Markdown-first durable ledger;
- raw source/tool-output references;
- ledger-aware compaction/resume;
- retrieval discipline for local models;
- whole-document mode for complete-coverage tasks;
- artifact manifest and finalization gates;
- worker state and acceptance discipline;
- selective validation contract for high-risk work.

The first useful surface is the run/eval substrate, not UI polish or ACP/AionUi.
UI/TUI/CLI controls matter, but they should expose runtime state rather than
define the product.

## 5. Non-Goals / Out Of Scope

1. No multi-tenant enterprise platform in v0.
2. No full governance, auth, audit retention, or deployment system in v0.
3. No user-facing task profiles for research/coding/planning/ideation in v0.
4. No autonomous per-turn model router in v0.
5. No JSONL/SQL as the model-authored ledger surface in v0.
6. No full validator engine before the ledger/eval foundation is proven.
7. No broad UI/control-plane build before runtime semantics are trustworthy.
8. No dynamic prompt/tool-surface mutation to activate ledger behavior mid-run.
9. No hidden semantic classifier deciding which raw outputs are important.
10. No overfitting Vesta to coding at the expense of research, planning,
    ideation, documents, and reflective work.

## 6. User Stories

1. As a local user, I want every Vesta run to have a durable `run_id` so that I
   can inspect what happened after compaction, failure, or interruption.
2. As a local user, I want Vesta to create run files at session start so that
   recovery does not depend on whether the agent remembered to initialize
   state later.
3. As a local user, I want `ledger.md` to record what is known, decided,
   missing, promised, and next so that conversation history is not the only
   memory.
4. As a local user, I want ledger entries to be Markdown so that I can read and
   edit decisions without database tooling.
5. As a local user, I want the runtime to add timestamps so that model guesses
   do not corrupt chronology.
6. As a local user, I want Vesta to preserve raw tool outputs outside prompt
   context so that evidence remains inspectable without bloating the model
   prompt.
7. As a local user, I want large raw outputs to have stable refs and excerpts so
   that reports can point to evidence without copying everything into the
   ledger.
8. As a local user, I want compaction to produce a resume packet from active
   working state so that a resumed model knows the actual next action.
9. As a local user, I want unfinished deliverables to survive compaction so that
   the model cannot forget promised work.
10. As a local user, I want final answers to be based on recorded state so that
    the agent cannot finish from vague memory of activity.
11. As a local user, I want artifact commitments tracked so that promised
    reports, plans, patches, and handoffs do not silently disappear.
12. As a local user, I want ordinary chat answers not to become artifacts unless
    there is a contract so that the ledger does not become noisy.
13. As a local user, I want material claims to have evidence or uncertainty
    labels so that important conclusions are reviewable.
14. As a local user, I want low-risk synthesis and ideation to remain fluid so
    that the runtime does not turn every conversation into research bureaucracy.
15. As a local user, I want retrieval to be locator-first by default so that
    local models do not waste time ingesting unnecessary source content.
16. As a local user, I want the model to be able to read whole documents when
    complete coverage is actually needed.
17. As a local user, I want whole-document processing to chunk large inputs and
    write chunk findings to the ledger so that long documents can be understood
    without relying on a single overlarge prompt.
18. As a local user, I want chunk findings to keep raw source refs so that
    important details can be reread instead of trusting summaries blindly.
19. As a local user, I want retrieval strictness to be controllable so that I
    can choose discipline or speed for the current run.
20. As a local user, I want broad-read gates to repair missing context without
    constantly interrupting me.
21. As a local user, I want retrieval thresholds to be configurable so that
    behavior can match my hardware and model context window.
22. As a local user, I want non-code runs to have the same run/ledger/artifact
    primitives as code runs so that research and planning are first-class.
23. As a local user, I want workspaces to represent a project or domain, not
    only a Git repo, so that document and planning runs are organized.
24. As a local user, I want raw retention to be local by default so that audit
    material stays on my machine.
25. As a local user, I want cleanup or purge controls so that raw retained data
    does not accumulate forever.
26. As a local user, I want model-facing excerpts to be redacted where
    appropriate so that secrets are not unnecessarily fed back into context.
27. As a local user, I want worker delegations to record objective, model lane,
    artifacts, failures, and gaps so that worker behavior is inspectable.
28. As a local user, I want parent agents to spot-audit high-materiality worker
    claims so that worker summaries are not accepted blindly.
29. As a local user, I want failed commands and tests to become visible state so
    that the final answer cannot hide them.
30. As a local user, I want unresolved contradictions to block or qualify final
    output so that conflicting evidence is not papered over.
31. As a local user, I want copied-repo execution for coding evals so that
    agent experiments do not damage the original workspace.
32. As a local user, I want prompt, config, model metadata, diff, tests,
    artifacts, ledger, and final verdict captured so that a run is repeatable
    and reviewable.
33. As a local user, I want Vesta to reuse Hermes storage and lifecycle
    primitives where sensible so that upstream alignment remains practical.
34. As a local user, I want Vesta to avoid broad core patches unless a lifecycle
    boundary needs a hook so that migration risk stays bounded.
35. As a local user, I want stable resident prompt/tool contracts so that local
    prompt cache behavior is not broken by dynamic instructions.
36. As a local user, I want repair failures to surface only when meaningful so
    that the runtime does not feel slower than the model.
37. As a future implementer, I want PRD-level decisions separated from task
    slices so that implementation planning can proceed without reopening
    product direction.
38. As a future team user, I want Vesta's local artifacts to be compatible with
    later audit and governance work even though v0 is personal/local first.
39. As a future UI user, I want retrieval strictness and whole-document
    thresholds exposed in UI/TUI/CLI so that runtime behavior is not hidden.
40. As a future validator author, I want validator expectations recorded before
    the full engine exists so that high-risk checks can grow incrementally.

## 7. Functional Requirements

### Run Substrate

1. Vesta MUST create a stable `run_id` at Vesta session start.
2. Vesta MUST create a run directory, `run.md`, and `ledger.md` immediately at
   session start.
3. Vesta MUST keep `run_id` separate from Hermes `session_id`.
4. Vesta MUST record Hermes session lineage inside run state.
5. Vesta SHOULD store run state under the active Hermes home using
   `get_hermes_home()`.
6. Vesta SHOULD group runs by deterministic normalized workspace hash.

### Ledger

1. Vesta MUST use Markdown as the model-facing ledger surface in v0.
2. Vesta MUST provide a dedicated `ledger_append` primitive for normal ledger
   writes.
3. `ledger_append` MUST keep model-provided input small: `entry_type`, `title`,
   `statement`, `refs`, `status`, `materiality`, and `next_action`.
4. Runtime MUST add id, timestamp, session/run metadata, and actor.
5. Runtime MUST own timestamps through `hermes_time.py` or a Vesta wrapper.
6. Ledger entries SHOULD be append-only and small.
7. Ledger state MUST distinguish claims, actions, artifacts, decisions, gaps,
   contradictions, commitments, worker state, checkpoints, and next steps.

### Raw Capture

1. Vesta MUST not inline large raw outputs in `ledger.md`.
2. Vesta SHOULD piggyback on Hermes tool-result persistence instead of copying
   the retention pipeline.
3. Vesta SHOULD route persisted outputs into the active run `raw/` directory.
4. Vesta MUST record stable refs, excerpts, hashes where available, tool name,
   arguments where appropriate, exit status where available, and capture time.
5. Runtime MUST NOT add a hidden semantic classifier for raw-output importance.

### Retrieval Discipline

1. Vesta MUST default to locator-first retrieval for normal source work.
2. The abstract retrieval rule MUST be: prefer the smallest source range that
   can answer the task honestly.
3. Full-document reading MUST remain allowed when complete coverage is needed.
4. Complete coverage MUST be treated as a deliberate retrieval contract, not the
   default source-reading path.
5. In `disciplined` mode, broad reads MUST repair only when locator history,
   complete-coverage need, and model-declared escalation reason are all absent.
6. In `permissive` mode, broad reads SHOULD proceed with lightweight ledger
   reason and raw refs.
7. v0 retrieval strictness MUST be two-state: `disciplined` and `permissive`.
8. v0 MUST NOT include an `off` mode for retrieval discipline.
9. Broad-read detection SHOULD consider line count, file size, token estimate,
   whole-file requests, repeated adjacent reads, and post-compaction rereads.
10. Broad-read thresholds MUST be configurable, not hidden constants.

### Whole-Document Mode

1. Whole-document mode MUST estimate token or size before ingestion.
2. If an artifact exceeds the configured threshold, Vesta MUST use
   chunk/ledger processing.
3. Chunking SHOULD prefer document structure when available and fall back to
   size-based chunking.
4. Each chunk SHOULD produce a ledger finding with source refs and unresolved
   gaps.
5. Each chunk after the first SHOULD receive a compact rolling recap of prior
   chunks, unresolved terms/questions, and the document objective as working
   context.
6. The rolling recap SHOULD be updated after each chunk and collapsed
   hierarchically if it grows too large.
7. Final synthesis SHOULD read from accumulated ledger findings.
8. High-materiality details SHOULD trigger targeted reread of the smallest raw
   range.
9. Whole-document thresholds MUST be user-controllable through UI/TUI/CLI or
   config. Until UI exists, config/CLI exposure is acceptable and missing UI is
   documented product debt.

### Compaction / Resume

1. Compaction MUST write a checkpoint entry.
2. Compaction MUST build a resume packet from active working state, not prose
   transcript summary.
3. Resume packet MUST include objective, phase, commitments, decisions, verified
   claims, open gaps, contradictions, worker status, artifact manifest, ledger
   path, and exactly one next action.
4. If a deliverable is unfinished, `next_action` MUST NOT be `None`.
5. After compaction, the first material action MUST consult resume packet and
   `ledger.md` status.
6. If no material state exists, Vesta SHOULD avoid ceremony.

### Gates And Finalization

1. Hard gates MUST use repair turns first.
2. Runtime MUST NOT silently auto-append semantic ledger entries.
3. Core gates SHOULD apply before compaction, before final response, after
   explicit user decision, and after artifact write.
4. Quality gates SHOULD apply after failed command/test, worker completion or
   failure, unresolved contradiction, and unsupported high-materiality claim.
5. Finalization MUST use bounded trust.
6. Finalization MUST check objective, commitments, artifacts, material claims,
   gaps, contradictions, worker state, verification or skip reason, and next
   action.
7. Non-code finalization MUST NOT require tests, diffs, or validators unless
   the task touches code, configuration, or risky operational behavior.

### Artifacts

1. Expected artifacts MUST be created only by user request, model commitment,
   worker contract, or known run path.
2. Normal chat answers MUST NOT automatically become artifacts.
3. Artifact tracking MUST be domain-neutral across reports, plans, decision
   memos, prompts, handoffs, patches, eval results, generated documents, and
   saved syntheses.

### Workers

1. v0 worker spawning MUST be explicit or config-driven, not autonomous routing.
2. Vesta SHOULD reuse Hermes `delegation.*` configuration first.
3. Worker state MUST record assigned objective, output contract, model/provider
   class without secrets, artifacts, failures, gaps, and next action.
4. Parent acceptance MUST require worker state, output refs or artifacts,
   declared gaps/failures, and spot audit for high-materiality claims.

### Raw Retention And Privacy

1. Raw outputs SHOULD be retained locally inside the run by default.
2. Vesta SHOULD provide cleanup/purge controls.
3. Vesta SHOULD support future TTL configuration.
4. Model-facing excerpts SHOULD be redacted where appropriate.
5. Raw payloads MAY remain unredacted as audit material, but this must be
   visible and controllable.

### Validator Boundary

1. v0 MUST record the selective validator contract.
2. v0 SHOULD run cheap deterministic or high-risk checks where available.
3. A full validator engine is out of scope until the ledger/eval foundation is
   proven.

## 8. UX Requirements

1. The user should not have to choose research/coding/planning profiles.
2. Retrieval strictness should be visible and controllable in UI/TUI/CLI, or
   config until UI exists.
3. Whole-document threshold should be visible and controllable in UI/TUI/CLI,
   or config until UI exists.
4. Repair gates should be model-facing first.
5. User interruption should happen only after repeated repair failure or a real
   preference choice.
6. UI activity notes should be compact and explain what gate fired without
   turning every repair into a user-facing prompt.
7. Prompt/tool surface should remain stable during a run to preserve local
   prompt-cache behavior.
8. Run artifacts should be easy to inspect from disk.
9. User-facing paths should use profile-aware display helpers.
10. Vesta should feel like a runtime assistant, not a form-heavy workflow tool.

## 9. Data / Integration Requirements

1. Use Hermes `get_hermes_home()` as the v0 root resolver.
2. Use Hermes `display_hermes_home()` for user-facing path display where
   applicable.
3. Reuse or wrap Hermes `hermes_time.py` / `hermes_time.now()` for all runtime
   timestamps.
4. Anchor Vesta runs to Hermes `session_id` and `task_id`, while preserving a
   separate `run_id`.
5. Record Hermes `parent_session_id` lineage for compaction continuation.
6. Reuse Hermes plugin hooks where sufficient: `on_session_start`,
   `on_session_end`, `pre_tool_call`, `post_tool_call`, `pre_llm_call`,
   `post_llm_call`.
7. Add narrow lifecycle hooks only where Hermes lacks a clean boundary,
   especially compaction/resume.
8. Piggyback on Hermes `maybe_persist_tool_result` and `BudgetConfig` for raw
   tool-output persistence.
9. Reuse Hermes `delegation.*` config for worker model lanes.
10. Keep secrets out of worker state and run metadata.
11. Store Vesta run state outside project repos by default.
12. Recommended storage shape:

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

## 10. Implementation Notes Already Decided

1. Plugin-first with minimal core hooks.
2. Keep Vesta state in files for v0.
3. Do not overload Hermes SQLite sessions as the Vesta run ledger.
4. Create run seed files eagerly.
5. Keep ledger behavior resident and stable from session start.
6. Do not dynamically inject ledger instructions every few turns.
7. Do not make user-facing profiles.
8. Do not implement automatic worker/model routing in v0.
9. Use `disciplined` retrieval as default.
10. Use `permissive` as the v0 escape hatch, not `off`.
11. Use repair-first gates.
12. Store dynamic state in `run.md` and `ledger.md`, not in changing prompt
    prefixes.
13. Treat Hermes alignment as implementation aid, not product veto.
14. Keep naming migration flexible; Vesta may rename Hermes primitives after
    behavior is proven.

## 11. Open Questions

1. What are the initial default values for broad-read line, byte, and token
   thresholds?
2. Which tokenizer or estimator should be used for local Qwen/Llama-style
   models?
3. What exact config keys or CLI commands expose retrieval strictness and
   whole-document thresholds before UI/TUI support exists?
4. What is the exact minimal compaction/resume hook API in Hermes?
5. How should workspace hashes be normalized for non-code/domain work?
6. What is the first cleanup/purge UX for retained raw payloads?
7. Which raw payload classes should be redacted before model-facing excerpts?
8. How deep should parent spot-audit be for worker high-materiality claims?
9. Which deterministic validator checks belong in the first v0 contract?
10. What exact artifact-manifest format should v0 use: Markdown only or a small
    generated JSON index beside Markdown?
11. How should Vesta expose current retrieval policy to the model without prompt
    churn?
12. How should Vesta represent document structure when chunking PDFs, Markdown,
    source files, and plain text?

## 12. Testing / QA Decisions

1. The first QA surface is repeatable eval/run harness behavior.
2. Tests should cover copied-repo run creation for coding tasks.
3. Tests should cover run state creation at session start.
4. Tests should cover runtime-owned timestamps.
5. Tests should cover `ledger_append` formatting and append-only behavior.
6. Tests should cover compaction checkpoint and resume packet generation.
7. Tests should cover `run_id` survival across Hermes session rotation.
8. Tests should cover raw-output spill into run `raw/` storage.
9. Tests should cover broad-read gate behavior in `disciplined` mode.
10. Tests should cover permissive mode reducing broad-read repair.
11. Tests should cover whole-document chunk/ledger processing.
12. Tests should cover rolling recap reinjection for later chunks in a long
    document.
13. Tests should cover finalization with supported and unsupported
    high-materiality claims.
14. Tests should cover finalization for non-code work without requiring tests or
    diffs.
15. Tests should cover worker state recording and parent acceptance checks.
16. Tests should cover prompt-cache-sensitive behavior by verifying stable
    prompt/tool surface across runtime policy changes.
17. Manual QA should inspect generated run directories and ledger readability.
18. Regression tests should ensure Vesta does not write run state into project
    repos by default.

## 13. Definition Of Done

The v0 PRD is satisfied when a Vesta-enabled local run can:

1. create stable run identity and seed files at session start;
2. keep a Markdown ledger updated through `ledger_append`;
3. preserve raw source/tool-output refs outside prompt context;
4. survive compaction with a ledger checkpoint and resume packet;
5. enforce retrieval discipline with `disciplined` and `permissive` modes;
6. process large complete-coverage documents through chunk/ledger workflow;
7. carry prior chunk recaps forward when processing later chunks;
8. keep whole-document thresholds configurable;
9. track declared artifacts and missing expected outputs;
10. record worker state and require parent acceptance for material worker output;
11. finalize from recorded state instead of conversation memory;
12. support non-code runs with the same workspace/run/ledger primitives;
13. run cheap deterministic/high-risk validator checks where available;
14. provide enough captured state for a human to inspect prompt/config/model
    metadata, ledger, raw refs, artifacts, failures, verification, and final
    verdict;
15. preserve local prompt-cache stability by avoiding dynamic prompt/tool
    surface mutation.

Design is complete. Implementation planning should decompose this PRD into
ordered local prototype slices without reopening accepted product semantics by
default.
