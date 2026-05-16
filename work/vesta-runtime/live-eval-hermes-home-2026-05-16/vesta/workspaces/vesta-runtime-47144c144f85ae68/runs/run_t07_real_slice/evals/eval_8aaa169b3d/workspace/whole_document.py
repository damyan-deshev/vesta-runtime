"""Whole-document processing for Vesta.

This is a runtime scaffolding path for complete-coverage document work. It
chunks large text artifacts, persists each chunk as raw evidence, and records
small ledger findings plus rolling recap context.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib

from vesta_runtime import append_ledger_entry, capture_raw_output


DEFAULT_TOKEN_THRESHOLD = 100_000
DEFAULT_MAX_CHUNK_TOKENS = 20_000
RECAP_CHAR_BUDGET = 4_000


@dataclass(frozen=True)
class WholeDocumentConfig:
    token_threshold: int = DEFAULT_TOKEN_THRESHOLD
    max_chunk_tokens: int = DEFAULT_MAX_CHUNK_TOKENS


def _as_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def load_whole_document_config() -> WholeDocumentConfig:
    try:
        from hermes_cli.config import load_config

        cfg = load_config()
    except Exception:
        cfg = {}
    vesta = cfg.get("vesta", {}) if isinstance(cfg, dict) else {}
    whole = vesta.get("whole_document", {}) if isinstance(vesta, dict) else {}
    if not isinstance(whole, dict):
        whole = {}
    return WholeDocumentConfig(
        token_threshold=_as_int(whole.get("token_threshold"), DEFAULT_TOKEN_THRESHOLD),
        max_chunk_tokens=_as_int(whole.get("max_chunk_tokens"), DEFAULT_MAX_CHUNK_TOKENS),
    )


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _chunk_lines(lines: list[str], *, max_chars: int) -> list[tuple[int, int, str]]:
    chunks: list[tuple[int, int, str]] = []
    current: list[str] = []
    start_line = 1
    current_chars = 0
    for idx, line in enumerate(lines, start=1):
        line_len = len(line)
        if current and current_chars + line_len > max_chars:
            chunks.append((start_line, idx - 1, "".join(current)))
            current = []
            start_line = idx
            current_chars = 0
        current.append(line)
        current_chars += line_len
    if current:
        chunks.append((start_line, start_line + len(current) - 1, "".join(current)))
    return chunks


def _collapse_recap(recap: str) -> str:
    if len(recap) <= RECAP_CHAR_BUDGET:
        return recap
    keep = RECAP_CHAR_BUDGET // 2
    return (
        recap[:keep].rstrip()
        + "\n\n[Earlier recap collapsed]\n\n"
        + recap[-keep:].lstrip()
    )


def process_document(
    *,
    path: str,
    objective: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Chunk a text document, record raw refs, and update the ledger."""

    doc_path = Path(path).expanduser().resolve()
    content = doc_path.read_text(encoding="utf-8", errors="replace")
    cfg = load_whole_document_config()
    estimated_tokens = estimate_tokens(content)
    max_chars = max(1, cfg.max_chunk_tokens * 4)
    lines = content.splitlines(keepends=True)
    if estimated_tokens <= cfg.token_threshold:
        chunks = [(1, len(lines) or 1, content)]
        chunking_reason = "under_threshold"
    else:
        chunks = _chunk_lines(lines, max_chars=max_chars)
        chunking_reason = "over_threshold"

    doc_hash = hashlib.sha256(str(doc_path).encode("utf-8")).hexdigest()[:10]
    doc_id = f"doc_{doc_hash}"
    rolling_recap = ""
    chunk_results: list[dict[str, Any]] = []

    for idx, (line_start, line_end, chunk_text) in enumerate(chunks, start=1):
        prior_recap = rolling_recap
        tool_use_id = f"{doc_id}_chunk_{idx:03d}"
        raw = capture_raw_output(
            content=chunk_text,
            source="whole_document",
            tool_use_id=tool_use_id,
            session_id=session_id,
            metadata={
                "document_path": str(doc_path),
                "chunk_index": idx,
                "chunk_count": len(chunks),
                "line_start": line_start,
                "line_end": line_end,
                "objective": objective,
            },
        )
        excerpt = " ".join(chunk_text.strip().split())[:500]
        statement = (
            f"Chunk {idx}/{len(chunks)} of {doc_path} covers lines "
            f"{line_start}-{line_end} for objective: {objective}. "
            f"Excerpt: {excerpt}"
        )
        append_ledger_entry(
            entry_type="document_chunk_finding",
            title=f"Document chunk {idx}/{len(chunks)}",
            statement=statement,
            refs=[raw["raw_ref"], f"{doc_path}:{line_start}-{line_end}"],
            status="active",
            materiality="medium",
            session_id=session_id,
            actor="runtime",
            structured_payload={
                "document_id": doc_id,
                "chunk_index": idx,
                "chunk_count": len(chunks),
                "line_start": line_start,
                "line_end": line_end,
                "prior_recap_chars": len(prior_recap),
            },
        )
        recap_addition = (
            f"Chunk {idx}/{len(chunks)} lines {line_start}-{line_end}: {excerpt}\n"
        )
        rolling_recap = _collapse_recap(rolling_recap + recap_addition)
        chunk_results.append({
            "chunk_index": idx,
            "line_start": line_start,
            "line_end": line_end,
            "raw_ref": raw["raw_ref"],
            "hash": raw["hash"],
            "prior_recap": prior_recap,
            "excerpt": excerpt,
        })

    append_ledger_entry(
        entry_type="document_recap",
        title="Whole-document rolling recap",
        statement=rolling_recap or "Document processed without chunk content.",
        refs=[str(doc_path)],
        status="active",
        materiality="medium",
        session_id=session_id,
        actor="runtime",
        structured_payload={
            "document_id": doc_id,
            "chunk_count": len(chunks),
            "estimated_tokens": estimated_tokens,
            "chunking_reason": chunking_reason,
        },
    )

    return {
        "document_id": doc_id,
        "path": str(doc_path),
        "objective": objective,
        "estimated_tokens": estimated_tokens,
        "token_threshold": cfg.token_threshold,
        "max_chunk_tokens": cfg.max_chunk_tokens,
        "chunking_reason": chunking_reason,
        "chunk_count": len(chunks),
        "chunks": chunk_results,
        "rolling_recap": rolling_recap,
    }
