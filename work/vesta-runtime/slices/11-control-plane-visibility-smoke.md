# Slice 11 - Control-Plane Visibility Smoke

Status: completed
Mode: AFK after resolved HITL, manual QA if UI exists
Blocked by: 00, 06, 07, 09

## User Value

TUI/ACP/dashboard surfaces can inspect Vesta run, worker, and finalization
state without becoming the source of truth.

## Sources

- PRD: UX Requirements, Data / Integration Requirements
- User stories: S17, S18, O01, O08
- Hermes overlap: extend existing TUI, dashboard PTY, ACP adapter, and
  spawn-tree visibility

## Accepted HITL Decisions

Resolved on 2026-05-16:

- Do not build a new UI first.
- CLI/file inspection is authoritative.
- TUI/ACP/dashboard are visibility smoke surfaces only after runtime artifacts
  exist.
- UI/control-plane state must read Vesta artifacts, not infer truth from live
  events.
- Browser QA applies only if a browser/dashboard surface exists.
- If browser automation or vision is unavailable, mark visual review as
  `manual-required`; do not claim visual QA.

## Hermes Surfaces To Reuse

- Hermes TUI and dashboard PTY bridge
- ACP adapter session/tool/progress events
- spawn-tree snapshots as visibility only
- session logs as supporting evidence

## Vertical Scope

Create a bounded local control-plane smoke:

1. Expose or link active Vesta run path from TUI/ACP/dashboard context.
2. Show enough run/session/worker/finalization status for postmortem.
3. Ensure UI state reads Vesta artifacts instead of inferring truth from live
   events.
4. Keep test local-only.
5. Mark remote/WebUI use out of scope.

## Interfaces / Contracts

Minimum visible fields:

- run id
- run path
- active Hermes session id
- ledger path
- worker summary
- finalization status
- latest next action

## Acceptance Criteria

- Operator can find the active run directory from the control surface.
- Worker state and finalization status match Vesta files.
- Missing or unavailable UI does not corrupt runtime state.
- Remote/browser surface is not assumed safe by default.

## Verification

Command target once implemented:

```bash
source .venv/bin/activate 2>/dev/null || source venv/bin/activate
pytest tests/vesta/test_control_plane_visibility.py -q
```

Manual/browser QA:

1. Start local TUI or dashboard if available.
2. Open the active run/status view or command.
3. Capture URL if browser-based.
4. Capture console errors and failed network requests.
5. Capture DOM/accessibility notes for the run/status labels.
6. Capture screenshot evidence if allowed.
7. If browser automation or vision is unavailable, mark visual review as
   manual-required and store screenshot/artifact paths only.

Visual inspection:

- Required for UI/dashboard path: no clipped status text, no missing run path,
  no misleading success state when finalization is blocked.
- Manual acceptable for TUI-only path.

## QA And Fix-Forward Gate

If UI/control-plane state disagrees with Vesta artifacts, fix before marking
the slice complete. UI visibility must remain downstream of runtime truth.

## Out Of Scope

- New polished GUI.
- Remote dashboard hardening.
- AionUi-specific integration beyond bounded local smoke.

## QA Result

Status: pass
Verification command: `uv run --extra dev pytest tests/vesta -q`
Manual checks: Inspected generated control-plane snapshot through tests for run
path, ledger path, worker summary, finalization status, validator status, and
next action.
Visual/browser checks: manual-required; no new browser/dashboard UI was built
for v0, by accepted HITL decision.
Fix-forward notes: Implemented file-backed snapshot instead of UI logic so
future TUI/ACP/dashboard work can read Vesta artifacts as source of truth.
Residual risk: Dashboard/TUI visual integration remains future smoke work once a
specific surface is chosen.
