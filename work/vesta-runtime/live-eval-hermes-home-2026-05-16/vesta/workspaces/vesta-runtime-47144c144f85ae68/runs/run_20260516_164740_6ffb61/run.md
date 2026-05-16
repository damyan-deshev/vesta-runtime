# Vesta Run

Run ID: `run_20260516_164740_6ffb61`
Created At: `2026-05-16T16:47:40.775548+03:00`
Workspace Hash: `vesta-runtime-47144c144f85ae68`
Workspace Path: `/Users/damyandeshev/projects/vesta-runtime`
Hermes Session ID: `20260516_164740_8b2735`
Hermes Parent Session ID: ``
Task ID: `a53f46a5-b8d8-4b23-ae2c-713cd2eb9492`
Model: `Qwen3.6-27B-MTP-Q6_K`
Provider: `custom`
Platform: `cli`

## Hermes Session Lineage

- 20260516_164740_8b2735

## Prompt / Cache Contract

- Vesta state is file-backed.
- Runtime policy should not mutate system prompt or tool surface mid-run.

## Artifacts

- Ledger: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164740_6ffb61/ledger.md`
- Resume packet: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164740_6ffb61/resume-packet.md`
- Artifact manifest: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164740_6ffb61/artifact-manifest.md`
- Finalization: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164740_6ffb61/finalization.md`
- Worker state: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164740_6ffb61/worker-state.md`
- Validator result: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164740_6ffb61/validator-result.md`
- Control plane snapshot: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164740_6ffb61/control-plane.md`
- Handoff: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164740_6ffb61/handoff.md`
- Raw index: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164740_6ffb61/raw/index.md`

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

