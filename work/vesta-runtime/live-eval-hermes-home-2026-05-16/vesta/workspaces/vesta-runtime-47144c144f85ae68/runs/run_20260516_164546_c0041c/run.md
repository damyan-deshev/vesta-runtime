# Vesta Run

Run ID: `run_20260516_164546_c0041c`
Created At: `2026-05-16T16:45:46.571587+03:00`
Workspace Hash: `vesta-runtime-47144c144f85ae68`
Workspace Path: `/Users/damyandeshev/projects/vesta-runtime`
Hermes Session ID: `20260516_164546_d76739`
Hermes Parent Session ID: ``
Task ID: `5efa4db4-c0c4-4e5d-ab8e-226d06bf5523`
Model: `Qwen3.6-27B-MTP-Q6_K`
Provider: `custom`
Platform: `cli`

## Hermes Session Lineage

- 20260516_164546_d76739

## Prompt / Cache Contract

- Vesta state is file-backed.
- Runtime policy should not mutate system prompt or tool surface mid-run.

## Artifacts

- Ledger: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164546_c0041c/ledger.md`
- Resume packet: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164546_c0041c/resume-packet.md`
- Artifact manifest: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164546_c0041c/artifact-manifest.md`
- Finalization: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164546_c0041c/finalization.md`
- Worker state: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164546_c0041c/worker-state.md`
- Validator result: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164546_c0041c/validator-result.md`
- Control plane snapshot: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164546_c0041c/control-plane.md`
- Handoff: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164546_c0041c/handoff.md`
- Raw index: `/Users/damyandeshev/projects/vesta-runtime/work/vesta-runtime/live-eval-hermes-home-2026-05-16/vesta/workspaces/vesta-runtime-47144c144f85ae68/runs/run_20260516_164546_c0041c/raw/index.md`

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

