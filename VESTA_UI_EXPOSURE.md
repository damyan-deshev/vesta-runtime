# Vesta UI Exposure

Date: 2026-05-22

## Purpose

Vesta runtime state must be inspectable without reading raw run files by hand.
The first UI exposure layer is deliberately small: surface the current run,
finalization verdict, artifact state, worker state, validator state, lineage,
ledger path, blockers, and next action through the existing Hermes TUI and
dashboard surfaces.

## Dependencies

The dashboard and embedded TUI are optional Hermes surfaces. For Vesta UI work,
the canonical local install is:

```bash
pip install -e '.[web,pty]'
```

`web` installs FastAPI/Uvicorn for the dashboard API. `pty` installs
`ptyprocess` on POSIX so `/chat` can embed the real `hermes --tui` through a
pseudo-terminal. The project already declares both extras in `pyproject.toml`;
do not add these packages to core dependencies unless the base non-dashboard
runtime starts requiring them.

Frontend assets require the normal dashboard Node dependencies:

```bash
cd web
npm ci
npm run build
```

## Surfaces

- TUI `/status` / `session.status`: appends a Vesta block when run state is
  available for the active Hermes session or session lineage. The block includes
  main model and validator model lane metadata when the run captured it.
- Dashboard REST:
  - `GET /api/sessions/{session_id}/vesta`
  - `GET /api/vesta/runs`
  - `GET /api/vesta/runs/{run_id}/status`
- Dashboard Chat sidebar: shows Vesta finalization, run id, validator status,
  main/validator model lanes, artifact counts, worker counts/blockers, next
  action, and run path.
- Dashboard Config: exposes Vesta retrieval/eval settings under the `Vesta`
  category, including retrieval strictness and eval contract profile.

## QA Commands

Use an isolated Hermes home for UI smoke tests:

```bash
HERMES_HOME=/private/tmp/vesta-runtime-test-home \
  python -m pytest tests/vesta tests/test_tui_gateway_server.py tests/hermes_cli/test_web_server.py \
  -q -k "vesta or session_status or state_readers or schema"

npm --prefix web run build
```

For visual QA, seed a sample Vesta run in an isolated `HERMES_HOME`, start:

```bash
HERMES_HOME=/private/tmp/vesta-ui-qa-home \
  hermes dashboard --tui --port 9123 --host 127.0.0.1 --no-open --skip-build
```

Then inspect `/config` and `/chat?resume=<session_id>`.

The browser protocol should verify both DOM and screenshots:

- Vesta config category exposes `vesta.retrieval.mode` and
  `vesta.eval.contract_profile`.
- Chat sidebar shows the Vesta run id, finalization verdict, validator status,
  main model, validator model, artifacts, workers, and next action.
- No fallback cloud model label such as Claude/Sonnet appears for the local
  llama.cpp setup.
- `custom` endpoints with `api_key: no-key-required` and a real `base_url`
  must not show a missing API key warning.

For the local llama.cpp setup used in the current Vesta evals, the dashboard
test profile should reflect the real lanes instead of fallback/default cloud
model labels:

```yaml
model:
  default: Qwen3.6-27B-MTP-Q6_K
  provider: custom:vesta-local-llama
  base_url: http://192.168.1.117:1234/v1
  api_key: no-key-required
  api_mode: chat_completions
  context_length: 196608

delegation:
  model: Qwen3.6-35B-A3B-MTP-UD-Q8_K_XL
  provider: custom:vesta-local-llama
  base_url: http://192.168.1.117:1234/v1
  api_key: no-key-required
  api_mode: chat_completions
```
