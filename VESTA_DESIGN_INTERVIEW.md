# Vesta Runtime Design Interview

Date: 2026-05-16

## Decisions Made

1. **v0 target: personal/local first.**
   Vesta v0 targets Damyan's local/private workflows first, with
   enterprise-compatible artifacts from the beginning: copied repos, ledger,
   eval runs, finalization gates, and validator hooks. It will not start as a
   multi-tenant enterprise platform.

2. **First v0 surface: eval harness first.**
   The first useful surface is a repeatable eval/run harness, not CLI/TUI polish
   and not ACP/AionUi integration. The harness should prove the runtime value:
   copied repo, prompt/config capture, artifacts, ledger, diff, tests, failures,
   and final verdict.

3. **Implementation focus: runtime discipline before product UI.**
   Future coding work should improve runtime behavior: state, artifacts,
   compaction/resume, evidence capture, and finalization gates. UI/control-plane
   work comes after the core run can be trusted.

4. **First runtime implementation package must include scaffold plus ledger/compaction.**
   Scaffold-only is not enough. The initial implementation package needs enough
   eval-run structure, ledger state, and compaction/resume behavior together to
   create a broad test surface.

5. **Ledger is the runtime memory substrate.**
   The ledger is not a transcript summary and not a research-report database. It
   is durable epistemic, operational, and artifact state shared across research,
   coding, planning, ideation, and reflective discussion. See
   `VESTA_LEDGER_DESIGN.md`.

6. **Vesta is broader than a coding agent.**
   It should behave like a personal work/runtime layer for Damyan: coding,
   research, planning, ideation, reflective discussion, decisions, artifacts,
   and follow-through. Coding evals are the first hard test surface, not the
   whole product identity.

7. **v0 ledger is Markdown-first and continuously updated.**
   The model-facing ledger is `ledger.md`, updated after material actions during
   the run. JSONL/SQLite can come later as generated indexes; they are not the
   model-authored surface in v0.

8. **Ledger prompting must preserve prompt-cache stability.**
   Ledger behavior should live in a small resident runtime protocol and stable
   tool descriptions. Dynamic ledger state stays in files and is read on demand,
   especially after compaction/resume, instead of being injected intermittently.

9. **Ledger writes use a dedicated `ledger_append` primitive.**
   The model should not patch the whole `ledger.md` for normal updates. A
   dedicated append tool should accept a small structured request and let the
   runtime format the Markdown entry with timestamp/session/run metadata.

10. **v0 `ledger_append` input stays small.**
   The model supplies only `entry_type`, `title`, `statement`, `refs`, `status`,
   `materiality`, and `next_action`. Runtime adds id, timestamp, session, run
   directory, and actor.

11. **Hard gates use repair turns first.**
    If required ledger state is missing at a boundary, runtime asks for a
    short repair turn that calls `ledger_append`. It blocks only if repair
    fails. Runtime should not silently auto-append semantic entries.

12. **Expanded hard gates have two bands.**
    Pass 1 covers core flow: compaction, final response, explicit user decision,
    and artifact write. Pass 2 covers quality/failure flow: failed command/test,
    worker completion/failure, unresolved contradictions, and unsupported
    high-materiality claims.

13. **Declared artifacts use hybrid ownership.**
    Runtime declares artifacts from commitments, output contracts, and known run
    paths. The model can declare semantic artifacts through `ledger_append`.
    Explicit user requests override both. Runtime may mechanically register raw
    payloads, but should not invent semantic artifact meaning without a
    commitment, path contract, or model/user declaration.

14. **Align scope primitives with existing Hermes shape.**
    Hermes already has a strong `session_id` primitive, SQLite session storage,
    parent/child session lineage for compression and branching, and `task_id`
    tool isolation. Vesta should not replace those. In v0, workspace maps to
    existing cwd/profile/project context, session maps to Hermes session lineage,
    and run becomes a small Vesta layer anchored by `session_id` and `task_id`
    with its own run directory, ledger, artifacts, resume packet, and final
    verdict.

15. **Vesta `run_id` is separate from Hermes `session_id`.**
    A Vesta run must survive Hermes compression rotation. The run keeps a
    stable `run_id` and records the Hermes session lineage inside run state
    rather than equating run identity with a single session row.

16. **Vesta run storage follows Hermes path conventions.**
    Default run state lives under the active Hermes home, using
    `get_hermes_home()` as the single source of truth and a checkpoint-like
    hashed workspace layout. This keeps Vesta profile-aware and aligned with
    upstream storage patterns while avoiding project-repo pollution.

17. **No user-facing task profiles in v0.**
    Hermes does not currently force users to choose between research/coding/
    planning/ideation profiles. Vesta should keep that product direction:
    one broad runtime substrate, with internal event-driven policies for
    evidence, artifacts, workers, verification, and decisions. The user should
    not have to pick a mode before asking for work.

18. **Worker delegation should support an adjacent model lane.**
    Vesta should use Hermes' existing `delegation.*` configuration first so
    workers can run on a different provider/model from the parent. This matters
    for local runs: a dense main model can keep its prompt cache hot while
    bounded subtasks run on a faster adjacent model, such as an MoE worker.

19. **v0 worker spawning is explicit/config-driven, not autonomous routing.**
    Vesta v0 may use a configured worker lane and the model may explicitly
    delegate bounded side tasks through Hermes `delegate_task`, but Vesta should
    not introduce an automatic per-turn worker/model router yet.

20. **Implementation strategy: plugin-first with minimal core hooks.**
    Vesta should live mostly as a Hermes plugin/tool/runtime layer: ledger
    tools, run directory, artifact manifest, worker tracking, and hook-based
    observation. Direct core patches should be limited to lifecycle boundaries
    Hermes does not expose cleanly yet, especially compaction/resume checkpoint
    integration.

21. **Do not reduce the design to implementation slices yet.**
    At this stage, the work is still product/runtime design. The design should
    capture the expanded v0 package, including quality/failure behavior, without
    prematurely slicing implementation work. Task slicing is a later handoff
    problem for the coding agent.

22. **Finalization should use bounded trust, not maximal suspicion.**
    Vesta should require evidence for high-materiality factual claims, risky
    changes, contradictions, declared artifacts, and final report claims. It
    should not require source-grade evidence for every low-risk interpretation,
    planning move, creative direction, or ordinary model judgment. Unknowns can
    be labeled, deferred, or accepted with low confidence instead of forcing
    endless research loops.

23. **Ledger activation should not be dynamic per turn.**
    Dynamic "turn ledger on now" behavior would add backend classification
    complexity and could change the prompt/tool surface mid-session, hurting
    local prompt-cache similarity. In a Vesta-enabled session, the resident
    ledger protocol and tools should be present from the start. Runtime state
    and gate strictness may remain light until material work appears, but the
    model-visible contract stays stable.

24. **Vesta-native sessions have ledger/run by default.**
    Hermes is the upstream parent and near-term implementation base, not the
    long-term product boundary. In Vesta proper, the ledger/run contract is a
    default product characteristic, not optional overhead. A Hermes-compatibility
    or debug mode may exist, but the Vesta entrypoint should assume durable
    runtime state from the start.

25. **Vesta creates run state immediately at session start.**
    A Vesta session should create its `run_id`, run directory, `run.md`, and
    `ledger.md` immediately. Gates can stay dormant for low-materiality
    conversation, but the identity and files should exist before compaction,
    worker delegation, artifact creation, or finalization can need them.

26. **Timestamps are runtime-owned, never model-authored.**
    `created_at`, ledger entry timestamps, source capture times, artifact
    verification times, and checkpoint times must come from a single runtime
    clock path or explicit time tool. Reuse Hermes' existing `hermes_time.py`
    clock path as the migration anchor. The model should not invent
    timestamps, because that creates inconsistent run and ledger chronology.

27. **Session seed files are minimal but real.**
    Initial `run.md` should hold runtime metadata and control state:
    `run_id`, runtime-owned `created_at`, workspace path/hash, session lineage,
    model/provider/context info, ledger path, artifact manifest path, raw dir,
    current phase, gate state, and worker lane config. Initial `ledger.md`
    should hold the human-facing operational truth header plus a
    `session_started` entry, objective state, open gaps, and next action.

28. **Canonical timestamps use local timezone with explicit offset.**
    Vesta should store canonical timestamps as runtime-local RFC3339/ISO-8601
    strings with offset, e.g. `2026-05-16T14:32:10+03:00`. This is readable for
    the local workflow while remaining unambiguous. UTC can be generated later
    as an index/audit field if team or cross-machine workflows need it.

29. **Raw capture is mechanical; meaning is ledger-assigned.**
    Hermes currently persists transcripts and spills large tool results by
    size/budget, not by semantic evidence classification. Vesta should follow
    that direction: capture tool-call metadata and spill raw outputs
    deterministically, then let model/user ledger entries promote refs to
    evidence, source, artifact, contradiction, or failure.

30. **Piggyback Hermes tool-result persistence for raw capture.**
    Vesta should not rewrite raw-output retention. Reuse Hermes'
    `maybe_persist_tool_result` / budget logic and add only the narrow
    integration needed to point persisted outputs at the Vesta run `raw/`
    directory and record manifest/source refs.

31. **Retrieval discipline is always on, with an explicit whole-document path.**
    Vesta should steer agents toward locator-first retrieval for normal work:
    search or manifest first, read narrow windows, and attach large reads to a
    claim, question, or gap. This should be resident behavior, not a visible
    `research_worker` mode. Full-document reading remains allowed, but it is a
    deliberate complete-coverage path, not the default way to answer from a
    source. The model should prefer the smallest sufficient source range unless
    the user objective or task semantics require coverage of the whole
    artifact. For large documents, Vesta should chunk by token budget, append
    chunk findings and source refs to `ledger.md`, then synthesize from the
    ledger while keeping raw ranges available for targeted reread. The resident
    prompt should express this as an abstract rule, not as a list of trigger
    phrases that creates brittle local minima.

32. **Retrieval gates must be user-visible and runtime-configurable.**
    The broad-read repair gate should not trap the user in one fixed behavior.
    Vesta needs a UI-exposed retrieval strictness toggle/feature flag so a user
    can favor discipline or speed for the current run. The default remains
    disciplined locator-first retrieval. A relaxed/permissive setting may allow
    broad or complete reads with less repair back-and-forth, especially when
    the user prefers the model to ingest a whole artifact. This toggle should
    update run/runtime state and gate behavior, not add or remove system-prompt
    instructions mid-session, so prompt-cache stability remains intact.

33. **v0 retrieval strictness has two modes, not an off switch.**
    The v0 UI toggle should expose `disciplined` and `permissive`. Do not add
    `off` initially. `permissive` is enough to reduce broad-read friction while
    still preserving the Vesta contract: ledger reasons, raw refs, and durable
    run state. A full off switch would make the runtime less inspectable and
    should wait until there is evidence that permissive mode is still too
    intrusive.

34. **Disciplined broad-read gate blocks only missing context.**
    In `disciplined` mode, a broad read is repaired only when all three are
    missing: relevant locator history, complete-coverage need, and a short
    model-declared escalation reason. This keeps broad reads intentional without
    turning the runtime into a slow permission loop.

35. **Whole-document thresholds must be user-controllable.**
    Whole-document mode should estimate token size before ingestion. If the
    artifact exceeds a configurable threshold, it uses chunk/ledger processing.
    That threshold must be exposed through UI/TUI/CLI or config. Until a real UI
    exists, this is a documented product debt and should not become a hidden
    hardcoded constant.

36. **Compaction/resume enforces ledger continuity only when material.**
    After compaction, the first material action requires the model to consult
    the resume packet and `ledger.md` status before continuing. If there is no
    unfinished deliverable, commitment, material claim, worker, contradiction,
    or expected artifact, Vesta should avoid ceremony.

37. **Repair-turn UX is mostly model-facing.**
    Gate repairs should appear as concise model-facing tool errors plus a short
    UI activity note. The user should see an explicit choice only after repeated
    repair failure or when the runtime genuinely needs a human preference.

38. **Finalization is domain-neutral.**
    Outside coding, finalization checks objective, commitments, artifacts,
    material claims, gaps, contradictions, worker state, and next action. Tests,
    diffs, and validators apply only when the task actually touches code,
    configuration, or risky operational behavior.

39. **Artifacts become expected only through a contract.**
    An output is an expected artifact when created by user request, model
    commitment, worker contract, or known run path. A normal chat answer is not
    automatically an artifact.

40. **Worker output requires parent acceptance.**
    Parent acceptance requires worker state, output refs or artifacts,
    declared gaps/failures, and a spot audit for high-materiality claims.
    Worker summaries should not be accepted blindly.

41. **Raw retention defaults to local auditability.**
    Raw outputs are kept locally inside the run by default, with cleanup/purge
    controls and future TTL configuration. Model-facing excerpts should be
    redacted where appropriate. Raw payloads may remain unredacted because they
    are audit material, but this must be visible and controllable.

42. **Workspace is broader than a repo.**
    For non-code tasks, workspace means the current project/domain/person
    context, not only a Git repository. Document, research, planning, and
    reflective runs still get `run_id`, `ledger.md`, `raw/`, and artifacts.

43. **Selective validator is a v0 contract, not a full engine.**
    v0 should record the validator contract and run cheap deterministic or
    high-risk checks where available. A full validator engine comes after the
    ledger/eval foundation is proven.

44. **Whole-document chunks carry prior recap context forward.**
    Long-document chunking must not treat each chunk as an independent text.
    When reading chunk N, the model should receive a compact rolling recap of
    prior chunks, unresolved terms/questions, and the current document objective,
    then append chunk N findings to the ledger. The runtime should reinject
    recaps, not raw prior chunks, and should collapse recaps hierarchically when
    they grow too large.

## North Star

Vesta should make local agent work reviewable. A completed run should leave
enough evidence for a human to inspect what happened, what changed, what passed,
what failed, and which claims are grounded.

## Expanded v0 Runtime Scope

The design target is an expanded runtime package, not a narrow implementation
slice. It should cover:

1. **Runtime/eval foundation:** copied-repo run directory, prompt/config/model
   capture, artifact manifest, logs, diff, tests, result file, ledger, and
   compaction/resume checkpointing in one inspectable run.
2. **Ledger substrate:** Markdown-first `ledger.md`, raw source/tool payload
   refs, artifact refs, worker state, and active working state.
3. **Core hard gates:** compaction, final response, explicit user decision, and
   artifact write.
4. **Quality/failure hard gates:** failed command/test, worker completion or
   failure, unresolved contradictions, and unsupported high-materiality claims.
5. **Context discipline:** large tool-output storage, locator-first policies,
   whole-document chunk/ledger mode, and stronger ledger-aware
   compaction/resume.
6. **Finish discipline:** finalization gates for missing artifacts, unsupported
   claims, failed workers, skipped verification, and risky diffs.
7. **Risk review:** selective validator for behavior-preserving refactors,
   security/auth/credential changes, public API shapes, and broad diffs.
8. **Daily workflow path:** CLI/TUI integration once the run substrate is solid.
9. **Control-plane path:** ACP/AionUi smoke tests after runtime semantics are
   stable.
10. **Team path:** governance, isolation, auth, audit retention, and deployment
   only after the local/personal loop is proven.

## Open Assumptions

- Team/enterprise support remains a later path, not v0 scope.
- v0 decisions should avoid blocking future governance, audit, and isolation
  work.
- The initial implementation package should not be scaffold-only; it needs
  enough ledger and compaction behavior to test runtime semantics.
- Ledger strictness should be internal policy/facet behavior, not visible
  user-facing task profiles.
- Coding is the first test surface, not the product boundary.
- Prompt-cache stability is a first-class constraint for local llama.cpp style
  runs; avoid dynamic early-prompt injections.
- `ledger_append` should format Markdown; `read_file ledger.md` remains the
  model-facing read path.
- Rich fields such as confidence, tags, scope, and structured payload are later
  extensions, not v0 tool input.
- "Soft" ledger behavior means resident static instructions and stable tool
  descriptions only, not periodic runtime nudges.
- Declared artifact detection should be domain-neutral: reports, plans,
  decision memos, prompts, handoffs, patches, eval results, and saved
  syntheses can all be artifacts when declared or contract-bound.
- Existing Hermes `session_id`, `parent_session_id`, and `task_id` should be
  treated as integration anchors, not rewritten as Vesta concepts.
- A run can start with `session_id == task_id` as an anchor, but the Vesta
  identity is `run_id`; Hermes `session_id` is mutable lineage data.
- Run storage should mirror Hermes' existing state-dir style: profile-aware
  home, module-level base path, hashed workspace/project directories, and
  human-readable metadata files beside opaque hashes.
- Worker model routing should reuse Hermes `delegation.*` config before Vesta
  invents any new routing surface.
- Worker model routing is a prompt-cache strategy, not only a cost strategy:
  separate child contexts can avoid expensive main-model cache reprocessing.
- Automatic worker/model routing is a later capability. v0 delegation should be
  visible in run config, prompt/eval contract, or explicit model action.
- Vesta should prefer plugin/context-engine-adjacent integration over broad
  core edits, but may add narrow upstreamable lifecycle hooks where required.
- Current design work should define the expanded runtime package. It should not
  force task slicing before the architecture and product semantics are settled.
- Finalization should distinguish high-materiality claims from low-risk model
  judgment so the runtime remains useful instead of becoming an infinite
  evidence machine.
- Ledger availability should be a Vesta-native default, not a dynamic per-turn
  activation decision.
- Once a Vesta session starts, the prompt/tool surface should stay stable.
  Runtime may keep gates dormant for low-materiality chat, but it should not
  introduce new ledger instructions midstream.
- Hermes alignment is an implementation aid, not a product veto. Vesta naming
  and primitives may diverge as the fork becomes its own runtime.
- Vesta session start should eagerly create run identity and seed files. Avoid a
  lazy "does this run exist yet?" state machine.
- All timestamps should be supplied by runtime/tool code from `hermes_time.py`
  or its Vesta-renamed successor, not generated by the model in prose.
- Canonical timestamps should use the runtime's local timezone with explicit
  offset. UTC may be generated later as secondary indexed metadata.
- `run.md` is runtime metadata/control state; `ledger.md` is human-facing
  operational truth. Do not collapse them into one seed file.
- Vesta should not add a runtime classifier that decides whether a raw output is
  semantically important. Store mechanics first; meaning belongs in ledger refs.
- Vesta raw capture should reuse Hermes' existing spill/preview/turn-budget
  behavior. If Vesta needs durability, redirect or extend that path; do not
  build a parallel raw-output pipeline.
- Locator-first retrieval is the default discipline for ordinary source work,
  but Vesta must preserve a deliberate full-document path for tasks where the
  user wants global understanding rather than a targeted claim lookup.
- Complete coverage is an explicit retrieval contract. A whole-file/document
  read should require either clear user intent, task semantics that genuinely
  depend on complete coverage, or a short model-declared reason recorded in the
  ledger. Otherwise, use locator-first retrieval.
- Whole-document mode should be chunked for large inputs, ledger-backed, and
  raw-reference preserving. Chunk summaries alone are not enough for
  high-materiality details; the model must be able to reread the smallest raw
  range needed.
- Retrieval strictness should be visible and controllable in the UI/TUI/CLI.
  The user should be able to relax broad-read gates when the gate costs more
  time than the extra context would.
- v0 retrieval strictness should be two-state: `disciplined` and `permissive`.
  Avoid an `off` mode until the product proves it is needed.
- Whole-document token thresholds and broad-read strictness should be
  user-controllable through UI/TUI/CLI or config. Lack of UI is product debt,
  not permission to hide constants.
- Whole-document chunk processing should carry forward accumulated recap
  context so later chunks can be understood in relation to earlier sections.
- Repair gates should be model-facing first and user-facing only when a real
  choice or repeated failure exists.
- Non-code work must keep the same run/ledger/artifact primitives as code work.

## Risks

- If v0 overfits to personal workflow, later team adoption may require rework.
- If enterprise concerns are pulled in too early, core harness discipline may
  stall.
- If UI/control-plane work starts too early, it may hide weak runtime semantics.
- If the expanded scope is handed directly to a coding agent without a later
  execution plan, implementation may sprawl. That should be solved in the
  next-day handoff, not by narrowing the design prematurely.
- If ledger schema becomes too rich too early, implementation will stall.
- If ledger nudges are injected intermittently, prompt-cache similarity may
  degrade and local runs may become slower/noisier.
- If the model patches the whole ledger directly, long runs may hit patch
  failures, context churn, or concurrent worker collisions.
- If artifact declaration relies only on runtime path heuristics, Vesta will
  overfit coding artifacts and miss planning/research/ideation deliverables.
- If artifact declaration relies only on model memory, promised outputs can
  silently disappear.
- If Vesta overloads Hermes session storage as the run ledger, it will increase
  migration risk and couple product semantics to transcript storage.
- If `run_id` equals `session_id`, compaction can split one logical run across
  multiple identities and make artifacts/ledger/finalization harder to trust.
- If Vesta invents a separate home/config resolution path, it risks cross-profile
  data bugs and needless upstream divergence.
- If Vesta exposes task profiles too early, it adds user-facing choice and
  routing complexity before the substrate proves it needs that shape.
- If Vesta auto-routes every turn between models, it may recreate the same
  prompt-cache instability the ledger design is trying to avoid.
- If Vesta is implemented as broad direct core patches, upstream alignment will
  degrade quickly.
- If Vesta insists on pure plugin integration with no new lifecycle hook, it
  may fail to enforce compaction/resume ledger behavior reliably.
- If finalization demands evidence for everything, it will create endless
  research loops and make the agent worse at practical work.
- If finalization trusts everything equally, the ledger becomes decorative and
  cannot protect important outputs.
- If Vesta dynamically activates ledger behavior mid-session, it risks both
  backend classifier complexity and prompt-cache churn.
- If Vesta creates heavy finalization pressure for casual low-materiality chat,
  it will feel bureaucratic. The solution is light/dormant gates, not dynamic
  prompt mutation.
- If Hermes compatibility is treated as the product boundary, Vesta will inherit
  upstream constraints longer than necessary.
- If run files are lazy-created, compaction/resume and first-material-action
  paths need extra missing-state recovery logic.
- If the model authors timestamps directly, `run.md`, `ledger.md`, source refs,
  and artifact manifests can disagree about chronology.
- If `run.md` and `ledger.md` duplicate the same purpose, session state will
  become noisy and harder to compact/resume.
- If raw-output capture depends on a semantic runtime classifier, Vesta gains a
  fragile hidden judge and another failure mode.
- If Vesta copies Hermes raw-output retention instead of piggybacking on it,
  small upstream changes in tool-result handling can silently diverge.
- If locator-first retrieval becomes an absolute ban on broad reads, Vesta will
  fail at document understanding, literature review, reflective analysis, and
  other non-coding workflows.
- If whole-document mode is triggered by a brittle list of examples or keywords,
  the model may overfit inference-time behavior and read too much or too little
  for nearby tasks.
- If whole-document mode keeps only summaries and loses raw refs, synthesis can
  become unrecoverable after a bad chunk summary.
- If retrieval gates are not user-visible, Vesta may create avoidable
  model/runtime back-and-forth and feel slower than simply reading the artifact.
- If retrieval toggles mutate the prompt/tool surface mid-session, they can
  undermine the prompt-cache stability Vesta depends on for local models.
- If whole-document thresholds are hidden constants, users cannot trade speed
  against context discipline for their hardware and task.
- If repair UX is too visible, the harness will feel slower than the model; if
  it is completely invisible, the user loses control.
- If non-code work lacks clear workspace semantics, Vesta will quietly collapse
  back into a coding harness.
- If worker summaries are accepted without parent audit, delegated failures can
  look like successful orchestration.
- If chunked long-document reads omit prior recap context, later chunks may be
  misinterpreted because they depend on definitions, setup, or arguments from
  earlier chunks.

## Design Phase Status

Design phase is done as of 2026-05-16. Remaining work should move into a
separate implementation planning/handoff phase, not more product semantics.
