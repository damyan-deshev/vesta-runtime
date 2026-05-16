# Slice 04 - Whole-Document Chunking With Rolling Recap

Status: ready
Mode: AFK
Blocked by: 00, 01, 02, 03

## User Value

When the user needs complete coverage of a long document, Vesta reads it
deliberately in chunks, writes findings to the ledger, and carries prior context
forward so later chunks are not interpreted in isolation.

## Sources

- PRD: Whole-Document Mode
- User stories: C15, C16, C17, E06
- Hermes overlap: build workflow on top of existing paginated reads and output
  caps

## Hermes Surfaces To Reuse

- `read_file(offset, limit)`
- output caps and raw refs
- retrieval config plumbing from Slice 03

## Vertical Scope

Implement complete-coverage document processing:

1. Detect explicit complete-coverage contract.
2. Estimate size/token count before ingestion.
3. Choose whole read if under threshold, otherwise chunk.
4. Prefer document structure when available; fall back to size chunks.
5. For each chunk, write ledger finding with source refs and gaps.
6. For chunk N, reinject compact rolling recap of chunks 1..N-1, unresolved
   terms/questions, and document objective.
7. Collapse recap hierarchically if it grows too large.
8. Final synthesis reads accumulated ledger findings and targeted raw refs.

## Interfaces / Contracts

Document run state:

```text
document_id:
objective:
coverage_mode: complete
chunk_count:
current_chunk:
rolling_recap_ref:
open_questions:
source_refs:
```

Ledger entry types:

- `document_chunk_finding`
- `document_recap`
- `gap`
- `claim`
- `next_step`

## Acceptance Criteria

- Long document is not shoved into context as a single raw blob when above
  threshold.
- Every chunk produces a concise ledger finding.
- Later chunks receive prior recap context.
- Final synthesis references accumulated findings and can reread small raw
  ranges for high-materiality details.
- Locator-first source behavior still applies outside whole-document mode.

## Verification

Command target once implemented:

```bash
source .venv/bin/activate 2>/dev/null || source venv/bin/activate
pytest tests/vesta/test_whole_document_mode.py -q
```

Manual checks:

1. Use a synthetic long Markdown document with terms introduced early and used
   later.
2. Force chunking via low threshold.
3. Confirm chunk 2+ receives prior recap.
4. Confirm final synthesis uses ledger findings, not raw prior chunks.

Visual inspection:

- Required: inspect `ledger.md` for readable chunk findings and recap growth.
- Browser automation: not applicable.

## QA And Fix-Forward Gate

If chunk findings are too verbose, missing refs, or later chunks lack prior
recap, fix before compaction/finalization. Long-document behavior becomes a
core regression fixture after this slice.

## QA Result

Status: pass
Verification command: `uv run --extra dev pytest tests/vesta -q`
Manual checks: focused tests cover threshold-forced chunking, raw refs, chunk
ledger findings, rolling recap, and prior recap delivered to later chunks.
Visual/browser checks: not applicable.
Fix-forward notes: none for this slice.
Residual risk: current chunk findings are deterministic scaffold summaries;
model-authored semantic summaries can be layered on the same ledger/raw refs
later.

## Out Of Scope

- PDF-specific parsing beyond available text extraction.
- Perfect token counting for all local models.
- Scientific correctness beyond preserving source coverage and gaps.
