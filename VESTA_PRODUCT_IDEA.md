# Vesta Runtime Product Idea

Date: 2026-05-16

## Clean Idea

Vesta Runtime is a local/private agent runtime for auditable long-running coding
and research work on sensitive codebases. It starts from a Hermes fork, but the
product focus is stricter harness discipline: copied-repo execution, durable
claim/source/gap ledger, raw tool-output artifacts, ledger-aware
compaction/resume, finalization gates, repeatable eval runs, and selective
validator review for high-risk patches.

## Problem

Local coding models can do useful real work, but harness quality decides whether
the result is trustworthy. Current agent runs can pass tests or produce a
plausible report while still hiding semantic drift, missing artifacts, weak
evidence, lost compaction state, excessive context churn, or truncated
delegation.

## Target Users

- Explicit: Damyan's local/private coding and research workflows.
- Inferred: senior engineers and platform/infra people working with private
  codebases and local model endpoints.
- Hypothesis: small teams or enterprises that need private on-prem agent
  capacity, after the personal/local workflow is proven.

## Desired Outcome

A local agent run should finish with inspectable evidence, not just a confident
answer. For code work, Vesta should preserve the prompt, copied repo, config,
model metadata, tool outputs, ledger, diff, tests, validator findings, failures,
and final judgment.

## Constraints And Preferences

- Position on privacy, control, repeatable capacity, and auditability; not
  "faster than frontier cloud models."
- Work on copied repos by default, not originals.
- Keep upstream Hermes sync practical; avoid mixing rename churn and behavior
  changes.
- Treat AionUi as an ACP/control-plane test client, not the core product
  boundary.
- Put evidence, lifecycle, and safety guarantees in runtime state/tool wrappers,
  not only prompts.

## First Research Direction

Research should compare Vesta's proposed harness discipline against Hermes,
OpenHands, Kilo Code, Pi, Codex-style workflows, and lightweight eval harnesses.
The first question is not whether local models can code; the question is what
runtime controls make local coding-agent output merge-reviewable.

## Resolved Direction

- v0 is personal/local first, with enterprise-compatible artifacts but not
  enterprise governance as the first product surface.
- The first surface is the eval/run harness and runtime discipline, not UI/TUI
  polish or ACP/AionUi.
- Hermes alignment is an implementation aid. Vesta may diverge in naming and
  primitives after the runtime behavior is proven.
- Selective validation is a v0 contract with cheap deterministic/high-risk
  checks where available. A full validator engine comes after ledger/eval
  foundation.
- AionUi is a useful ACP/control-plane test client, not the core product
  boundary.

## Design Phase Status

Design phase is complete as of 2026-05-16. The next phase should be an
implementation planning handoff that turns the accepted runtime semantics into
ordered work without reopening product direction by default.

## Research Handoff

I want to build a solution that solves this:

Vesta Runtime is a local/private agent runtime for auditable long-running coding
and research work on sensitive codebases. It productizes stricter harness
behavior around a Hermes fork: copied-repo execution, durable claim/source/gap
ledger, raw tool-output artifact storage, ledger-aware compaction and resume,
finalization gates, eval run capture, and selective validator review for
high-risk patches.
