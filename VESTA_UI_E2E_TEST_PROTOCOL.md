# Vesta UI E2E Test Protocol

This protocol defines the full UI/browser acceptance suite for Vesta runtime
visibility. It is intentionally broader than a single smoke prompt: Vesta is a
multi-surface runtime, so the UI must prove research, coding, delegation,
recovery, and blocked-state behavior without becoming the source of truth.

## Baseline Gate

Run before live UI work:

```bash
python -m pytest tests/vesta -q
scripts/run_tests.sh tests/vesta
python -m pytest tests/test_tui_gateway_server.py tests/hermes_cli/test_web_server_dashboard.py -q
npm --prefix web run build
npm --prefix ui-tui run build
```

Acceptance:

- No generated live-eval artifacts are staged.
- Dashboard/TUI uses the configured local llama.cpp models, not dummy or cloud
  model labels.
- Main lane and validator/delegate lane are visible where Vesta state exists.

## Browser QA Discipline

For each browser-backed scenario:

- Start the dashboard in an isolated `HERMES_HOME`.
- Capture the exact URL, session id, Vesta run dir, screenshot path, and any
  console/network errors.
- Inspect both DOM text and pixels; do not rely only on REST/API state.
- Inspect the Vesta run files after the UI run: `run.md`, `ledger.md`,
  `artifact-manifest.md`, `worker-state.md`, `validator-result.md`,
  `finalization.md`, `control-plane.md`, and `handoff.md` when present.
- Fix forward immediately when UI evidence contradicts runtime state.

## Required Scenarios

1. Startup and configuration

- Dashboard `/chat` loads the embedded `hermes --tui` terminal and the structured
  sidebar.
- Sidebar shows configured main model, connection state, and no false Vesta run
  before the first Vesta action.
- Model picker/config controls do not claim unavailable providers.

2. Research happy path

- Prompt a small real research task that must produce a markdown artifact.
- Expected result: ledger has material claim/gap entries, artifact exists,
  finalization is `accepted`, sidebar shows accepted verdict, model lanes,
  next action, run path, artifacts, and workers.

3. Coding/refactor on copied workspace

- Use a copied fixture, never the live UI source tree.
- Prompt a small behavior-preserving refactor.
- Expected result: locator-first reads, edit applied, compile/typecheck or
  focused test run executed, artifact/finalization state accepted or honestly
  blocked with evidence.

4. Blocked contract path

- Prompt a task that intentionally skips required Vesta tools or expected
  artifacts.
- Expected result: final prose cannot override runtime state; UI shows blocked
  finalization, blockers, and open artifacts.

5. Slow or stuck turn visibility

- Start a turn that takes long enough to inspect while running.
- Expected result: `/status` and dashboard sidebar show active turn elapsed
  time, last event, prompt preview, and interrupt-request state. The UI must not
  silently look idle while the model is still processing.

6. Delegation and validator path

- Run a two-lane validator/delegate task.
- Expected result: worker state captures worker id, child session/run ids,
  model lane, output contract, expected artifacts, final status, validator
  status, and parent acceptance. Sidebar/control-plane agree.

7. Resume and lineage

- Create or seed a blocked run, resume/recover it, and complete the missing
  artifact.
- Expected result: accepted recovery run clearly references the blocked run via
  lineage fields; UI does not present them as unrelated outcomes.

8. Compression/resume visibility

- Force compression with the deterministic hook rather than burning tokens.
- Expected result: compression telemetry explains trigger decision, resume
  packet keeps objective/next action, and UI state still points to the current
  run/session lineage.

9. Whole-document mode

- Use a long document where whole-document behavior is intended.
- Expected result: chunking, raw refs, rolling recap reinjection, and final
  synthesis are visible in ledger/run state without dumping the whole document
  into UI panels.

10. Cleanup and git hygiene

- Stop dashboard/TUI/worker processes.
- Confirm ignored live artifacts remain untracked.
- Commit only source, tests, and durable project docs.

## Evidence Record

Each full suite run should produce a short markdown report under ignored
`work/vesta-runtime/` with:

- environment and model lanes;
- commands run;
- scenario verdicts;
- screenshots/DOM notes;
- run dirs and key Vesta state files;
- fixes made during the pass;
- remaining gaps split into product bugs, test setup issues, and model behavior.
