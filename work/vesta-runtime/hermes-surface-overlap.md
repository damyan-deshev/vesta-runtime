# Hermes Surface Overlap Map

Date: 2026-05-16
Status: Source-audited overlap pass for Vesta user stories

This map marks where Vesta should reuse or extend existing Hermes surfaces
instead of rebuilding them. It is intentionally product-facing: the decision is
not "Hermes already solves it", but "what part of Hermes should Vesta piggyback
on before adding durable run/ledger semantics".

## Status Legend

- **Reuse:** Hermes already has a concrete primitive Vesta should call or wrap.
- **Extend:** Hermes has the adjacent mechanism, but Vesta must add run,
  ledger, manifest, or finalization semantics.
- **Build:** no meaningful Hermes surface found; Vesta should implement the
  product primitive.

## High-Impact Overlap

| Story area | Status | Existing Hermes surface | Vesta rewrite direction |
|---|---:|---|---|
| Stable run identity, resume, compaction lineage | Extend | `AIAgent(session_id, parent_session_id)`, `SessionDB.sessions.parent_session_id`, compaction-created child sessions, resume tip resolution | Keep Hermes `session_id` lineage, add stable Vesta `run_id` that owns all descendant sessions. |
| Eager run files and Markdown ledger | Build | Hermes has session JSON logs and SQLite transcript state, but no eager `run.md`/`ledger.md` | Build Vesta run directory and Markdown ledger as the model-facing runtime state. |
| Runtime timestamps | Reuse | `hermes_time.now()` | Standardize Vesta timestamps on this runtime clock instead of model-authored timestamps. |
| Raw evidence outside context | Extend | `tools/tool_result_storage.py`, tool output limits, terminal/background process buffers | Reuse spill/limit ideas, but store raw payloads under Vesta run `raw/` with refs, hashes, and retention state. |
| Locator-first retrieval | Extend | `search_files`, `read_file(offset, limit)`, read dedup/blocking, output limits, context reference caps | Add Vesta retrieval policy and ledger refs; do not rebuild the file tools. |
| Whole-document mode | Build on file tools | `read_file` pagination and output caps exist, but no chunk/ledger/rolling-recap workflow | Build complete-coverage document reader on top of existing file reads. |
| Retrieval strictness and thresholds | Extend | `DEFAULT_CONFIG`, `tool_output`, `file_read_max_chars`, CLI/config plumbing | Add Vesta config keys first; UI exposure can follow. |
| Worker delegation | Extend | `delegate_task`, delegation config, parent/child session IDs, TUI spawn-tree snapshots | Reuse worker spawning/model lane; add durable `worker_state`, acceptance, artifacts, and claim audit. |
| Worker model lane | Reuse/Extend | `delegation.provider/model/base_url/api_mode/reasoning_effort` | Use Hermes config-driven delegation as the v0 adjacent-model lane; avoid autonomous routing. |
| Copied-repo / safe coding workspaces | Extend | CLI `--worktree`, `.worktrees/hermes-*`, filesystem checkpoints | Reuse where applicable, but Vesta eval copied-repo discipline still needs original/copy manifest and run capture. |
| Profile-aware storage | Reuse | `get_hermes_home()`, `display_hermes_home()` | Store Vesta state under active Hermes home/profile; do not invent a parallel root. |
| Plugin/hook extension | Reuse/Extend | `pre_tool_call`, `post_tool_call`, `transform_tool_result`, `transform_terminal_output`, lifecycle hooks | Implement Vesta policy through plugins/hooks where enough; add narrow core hooks only for missing lifecycle boundaries. |
| TUI/ACP/control-plane visibility | Extend | Hermes TUI, dashboard PTY bridge, ACP adapter, spawn-tree overlay | Treat as control-plane candidates reading Vesta artifacts, not as the source of runtime truth. |
| Privacy/redaction | Extend | `security.redact_secrets`, `agent/redact.py`, redacting logs/tool outputs, checkpoint excludes | Reuse redaction primitives; add Vesta run-capture allow/deny manifests and raw purge semantics. |
| Validator | Build contract, reuse lanes | Guardrails and review-like maintenance exist, but no skeptical validator lane | Define Vesta validator output contract; later run it through delegation/auxiliary model surfaces. |

## Story Rewrite Index

| Story | Status | Rewrite note |
|---|---:|---|
| C01 Durable Run Identity | Extend | Stable `run_id` wraps Hermes rotating `session_id`/`parent_session_id` chain. |
| C02 Eager Run Files | Build | New Vesta files; only storage root/session metadata are reused. |
| C03 Operational Ledger | Build | Hermes transcript/memory are not the ledger. |
| C04 Model-Friendly Markdown Memory | Build | Markdown is a Vesta product surface; SQLite may index later. |
| C05 Runtime-Owned Time | Reuse | Use `hermes_time.now()` and audit direct timestamp paths as needed. |
| C06 Material Action Ledger Writes | Build/Extend | New ledger protocol, possibly enforced via existing post-tool/lifecycle hooks. |
| C07 Dedicated Ledger Append | Build/Extend | New tool/primitive registered through Hermes tool/plugin surface. |
| C08 Raw Evidence Outside Context | Extend | Move from temp spill previews to run-scoped raw refs. |
| C09 Ledger-Aware Compaction | Extend | Hook into Hermes compression lineage, but resume from ledger packet. |
| C10 Finalization From Recorded State | Build/Extend | Add finalization gate; can use lifecycle/finalize hooks where available. |
| C11 Evidence For High-Materiality Claims | Build | Model/ledger policy, not existing Hermes runtime logic. |
| C12 Artifact Commitments | Build/Extend | Session logs/trajectories exist; artifact manifest is Vesta. |
| C13 Non-Code First-Class Runs | Build | Product stance over the shared run substrate. |
| C14 Locator-First Retrieval By Default | Extend | Reuse `search_files`/`read_file`; add policy and repair gates. |
| C15 Complete-Coverage Document Reading | Build on tools | Use file pagination; add whole-document intent and coverage state. |
| C16 Chunk/Ledger Long-Document Understanding | Build | New chunk summaries, refs, and synthesis flow. |
| C17 Prior-Chunk Recap Context | Build | New rolling/hierarchical recap workflow. |
| C18 User-Controlled Retrieval Strictness | Extend | Add Vesta config/CLI keys using Hermes config plumbing. |
| C19 Configurable Whole-Document Thresholds | Extend | Add Vesta thresholds beside existing file/tool output limits. |
| C20 Worker State And Parent Acceptance | Extend | Reuse `delegate_task`; add durable worker manifest and acceptance gate. |
| C21 Adjacent Worker Model Lane | Reuse/Extend | Reuse `delegation.*` config; keep routing explicit. |
| S01 Copied-Repo Coding Runs | Extend | Consider Hermes `--worktree`; Vesta still needs copied corpus/run manifest. |
| S02 Prompt/Config/Model Capture | Extend | Hermes sessions store prompt/model metadata; Vesta writes run manifest. |
| S03 Verification Capture | Build/Extend | Tool transcript exists; Vesta must capture verification as first-class state. |
| S04 Failed Commands As State | Build/Extend | Tool failures exist in transcript; Vesta promotes material failures to ledger. |
| S05 Negative Evidence | Build/Extend | `search_files` returns zero matches; Vesta persists material negative evidence. |
| S06 Bounded Trust For Synthesis | Build | Ledger/finalization policy. |
| S07 Domain-Neutral Artifacts | Build/Extend | Artifacts can reuse storage conventions, but tracking is Vesta. |
| S08 Domain-Neutral Finalization | Build | Product finalization policy. |
| S09 Stable Prompt Cache Contract | Reuse/Extend | Hermes already preserves prompt prefix in continuations; Vesta keeps state in files. |
| S10 Repair-First Gates | Extend | Use pre-tool blocking/repair hooks; add Vesta stateful policy. |
| S11 Broad-Read Repair Without Drama | Extend | Use file tools plus pre-tool gate; add locator-history checks. |
| S12 Raw Retention Controls | Extend | Reuse redaction/output spill ideas; add run-scoped purge/manifest. |
| S13 Profile-Aware Storage | Reuse | Use `get_hermes_home()` and display helper. |
| S14 Small Plugin-First Extension | Reuse | Hermes plugin/hook system is the preferred extension seam. |
| S15 Selective Validator Contract | Build/Extend | Contract is Vesta; execution can reuse delegation/auxiliary lanes later. |
| S16 Validator Separation | Build | New reporting model. |
| S17 AionUi As Control-Plane Candidate | Extend | Prefer existing ACP/TUI surfaces for bounded tests. |
| S18 Process/Session Visibility | Extend | TUI/ACP/session logs exist; Vesta should expose run artifacts. |
| S19 Exact Source Locators | Extend | `read_file` line output and raw refs exist partially; Vesta source refs are new. |
| S20 Newest Instruction Wins | Extend | Resume/session search exists; ledger next action becomes authoritative. |
| E01-E07 | Extend/Build | Hermes compaction/retrieval primitives exist; Vesta adds ledger pressure and reread suppression. |
| E08 Prompt Cache Cliff | Reuse/Extend | Use Hermes stable prompt behavior; avoid dynamic prompt/tool churn. |
| E09 Incomplete Security Review | Build | Vesta finalization/gap policy. |
| E10 Failed Observation Process | Extend | Session/process surfaces exist; Vesta records end reason in run state. |
| E11 Sensitive Local Data Exclusion | Extend | Reuse redaction/checkpoint excludes; add Vesta corpus/run exclusion manifest. |
| E12 Permissive Read Still Auditable | Extend | Same retrieval tools, different policy strictness. |
| O01-O12 | Mostly Extend | Operator stories should read Hermes state where useful but present Vesta run state as the source of truth. |

## Implementation Bias From This Pass

1. Do not replace Hermes session storage. Add Vesta run identity above it.
2. Do not replace `read_file`, `search_files`, `delegate_task`, config loading,
   redaction, TUI, ACP, or profile-aware paths. Wrap or extend them.
3. Build new primitives only where Hermes is transcript-centric and Vesta needs
   durable runtime truth: `run.md`, `ledger.md`, raw refs, artifact manifest,
   worker manifest, resume packet, finalization packet, and long-document
   rolling recap.
4. Keep UI/control-plane work downstream of the runtime artifacts; UI snapshots
   are useful visibility, not authoritative state.
