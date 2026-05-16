# Vesta Run

Run ID: `run_t08_whole_doc`
Created At: `2026-05-16T17:11:36.468754+03:00`
Workspace Hash: `vesta-runtime-47144c144f85ae68`
Workspace Path: `/Users/damyandeshev/projects/vesta-runtime`
Hermes Session ID: `session_t08_whole_doc`
Hermes Parent Session ID: ``
Task ID: ``
Model: ``
Provider: ``
Platform: ``

## Hermes Session Lineage

- session_t08_whole_doc

## Prompt / Cache Contract

- Vesta state is file-backed.
- Runtime policy should not mutate system prompt or tool surface mid-run.

## Artifacts

- Ledger: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t08_whole_doc/ledger.md`
- Resume packet: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t08_whole_doc/resume-packet.md`
- Artifact manifest: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t08_whole_doc/artifact-manifest.md`
- Finalization: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t08_whole_doc/finalization.md`
- Worker state: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t08_whole_doc/worker-state.md`
- Validator result: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t08_whole_doc/validator-result.md`
- Control plane snapshot: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t08_whole_doc/control-plane.md`
- Handoff: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t08_whole_doc/handoff.md`
- Raw index: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t08_whole_doc/raw/index.md`

## Vesta Effective Config

- Retrieval Mode: `disciplined`
- Broad Read Line Threshold: `200`
- Broad Read Byte Threshold: `20000`
- Broad Read Token Threshold: `12000`
- Whole Document Token Threshold: `100000`
- Whole Document Max Chunk Tokens: `20000`
- Raw Retention Retain By Default: `True`
- Raw Retention Purge Preserves Manifest: `True`

## Prompt Cache Contract

- Runtime prompt/tool surface should remain stable within a run.
- Config changes are captured as run metadata, not injected as ad hoc prompt
  changes mid-session.

