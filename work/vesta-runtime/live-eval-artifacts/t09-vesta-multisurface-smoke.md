# T09: Vesta Multi-Surface Smoke Note

Vesta is a **multi-surface harness**, not only a coding-agent wrapper.
This note lists the surfaces it is designed to support, backed by source refs.

## 3 Non-Coding Harness Surfaces

1. **Research / Document Synthesis** — Vesta's ledger and whole-document
   chunking workflow are designed for research work: "local/private agent
   runtime for auditable long-running coding and research work"
   (`VESTA_PRODUCT_IDEA.md`, lines 7–8, 80–85). Chunk/ledger processing
   with rolling recaps is a first-class path for large document ingestion
   (`VESTA_LEDGER_DESIGN.md`, lines 178–209).

2. **Artifact Tracking (Domain-Neutral)** — Artifact recording covers
   "reports, plans, decision memos, prompts, handoffs, patches, eval
   results, generated documents, and saved syntheses" — not just code
   diffs (`prd.md`, lines 296–303).

3. **Selective Validation / Quality Gates** — v0 includes a selective
   validator contract and quality gates that fire on "unresolved
   contradiction, unsupported high-materiality claim, or failed command"
   independent of whether the run produces code (`prd.md`, lines 281–294,
   323–328).

## 2 Coding / Eval Surfaces

1. **Copied-Repo Coding Eval** — `coding_eval_start` / `coding_eval_capture`
   create isolated copied workspaces, record prompt/config/exclusion refs,
   and capture diff + verification output (`VESTA_PRODUCT_IDEA.md`, lines
   9–12, 33–35).

2. **Worker-Based Parallel Eval** — Explicit worker spawning with output
   contracts, model/provider metadata, and parent acceptance audits
   (`prd.md`, lines 305–312).

## 1 Caveat / Gap

**UI/TUI exposure for harness controls is product debt.** Retrieval
strictness toggles (`disciplined` vs `permissive`) and whole-document
thresholds are configurable but lack UI surfaces: "missing UI is
documented product debt" (`prd.md`, lines 264–266). Users currently set
these via config/CLI only.

## Source Refs

| File | Lines | Topic |
|------|-------|-------|
| `VESTA_PRODUCT_IDEA.md` | 1–85 | Product scope, research+coding positioning |
| `VESTA_LEDGER_DESIGN.md` | 154–248 | Retrieval discipline, chunking, toggles |
| `work/vesta-runtime/prd.md` | 195–329 | Run substrate, ledger, artifacts, gates, workers, validators |
