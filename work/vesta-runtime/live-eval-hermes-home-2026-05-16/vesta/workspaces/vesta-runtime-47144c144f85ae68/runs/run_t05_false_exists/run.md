# Vesta Run

Run ID: `run_t05_false_exists`
Created At: `2026-05-16T17:07:38.942351+03:00`
Workspace Hash: `vesta-runtime-47144c144f85ae68`
Workspace Path: `/Users/damyandeshev/projects/vesta-runtime`
Hermes Session ID: `session_t05_false_exists`
Hermes Parent Session ID: ``
Task ID: ``
Model: ``
Provider: ``
Platform: ``

## Hermes Session Lineage

- session_t05_false_exists

## Prompt / Cache Contract

- Vesta state is file-backed.
- Runtime policy should not mutate system prompt or tool surface mid-run.

## Artifacts

- Ledger: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t05_false_exists/ledger.md`
- Resume packet: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t05_false_exists/resume-packet.md`
- Artifact manifest: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t05_false_exists/artifact-manifest.md`
- Finalization: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t05_false_exists/finalization.md`
- Worker state: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t05_false_exists/worker-state.md`
- Validator result: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t05_false_exists/validator-result.md`
- Control plane snapshot: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t05_false_exists/control-plane.md`
- Handoff: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t05_false_exists/handoff.md`
- Raw index: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_t05_false_exists/raw/index.md`

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

