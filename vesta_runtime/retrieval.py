"""Vesta retrieval policy.

The policy is intentionally small and explicit: Hermes keeps the file tools;
Vesta decides when a broad read needs locator-first repair.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any
import os


DEFAULT_MODE = "disciplined"
DEFAULT_BROAD_READ_LINE_THRESHOLD = 200
DEFAULT_BROAD_READ_BYTE_THRESHOLD = 20_000
DEFAULT_BROAD_READ_TOKEN_THRESHOLD = 12_000

_LOCATOR_LOCK = Lock()
_LOCATOR_HISTORY: dict[str, list[dict[str, Any]]] = {}
_MAX_LOCATORS_PER_TASK = 100


@dataclass(frozen=True)
class RetrievalConfig:
    mode: str = DEFAULT_MODE
    broad_read_line_threshold: int = DEFAULT_BROAD_READ_LINE_THRESHOLD
    broad_read_byte_threshold: int = DEFAULT_BROAD_READ_BYTE_THRESHOLD
    broad_read_token_threshold: int = DEFAULT_BROAD_READ_TOKEN_THRESHOLD


def _as_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def load_retrieval_config() -> RetrievalConfig:
    """Load effective Vesta retrieval config from Hermes config."""

    try:
        from hermes_cli.config import load_config

        cfg = load_config()
    except Exception:
        cfg = {}
    vesta = cfg.get("vesta", {}) if isinstance(cfg, dict) else {}
    retrieval = vesta.get("retrieval", {}) if isinstance(vesta, dict) else {}
    if not isinstance(retrieval, dict):
        retrieval = {}
    mode = str(retrieval.get("mode", DEFAULT_MODE)).strip().lower()
    if mode not in {"disciplined", "permissive"}:
        mode = DEFAULT_MODE
    return RetrievalConfig(
        mode=mode,
        broad_read_line_threshold=_as_int(
            retrieval.get("broad_read_line_threshold"),
            DEFAULT_BROAD_READ_LINE_THRESHOLD,
        ),
        broad_read_byte_threshold=_as_int(
            retrieval.get("broad_read_byte_threshold"),
            DEFAULT_BROAD_READ_BYTE_THRESHOLD,
        ),
        broad_read_token_threshold=_as_int(
            retrieval.get("broad_read_token_threshold"),
            DEFAULT_BROAD_READ_TOKEN_THRESHOLD,
        ),
    )


def reset_locator_history(task_id: str | None = None) -> None:
    with _LOCATOR_LOCK:
        if task_id is None:
            _LOCATOR_HISTORY.clear()
        else:
            _LOCATOR_HISTORY.pop(task_id, None)


def record_locator(
    *,
    task_id: str,
    pattern: str,
    target: str,
    path: str,
    result_count: int | None = None,
) -> None:
    """Record a search/manifest action as locator history for a task."""

    entry = {
        "pattern": pattern,
        "target": target,
        "path": path,
        "result_count": result_count,
    }
    with _LOCATOR_LOCK:
        items = _LOCATOR_HISTORY.setdefault(task_id, [])
        items.append(entry)
        if len(items) > _MAX_LOCATORS_PER_TASK:
            del items[:-_MAX_LOCATORS_PER_TASK]


def has_locator_history(task_id: str) -> bool:
    with _LOCATOR_LOCK:
        return bool(_LOCATOR_HISTORY.get(task_id))


def _estimate_tokens_from_bytes(byte_count: int) -> int:
    # Conservative enough for broad-read gating without binding to one tokenizer.
    return max(1, byte_count // 4)


def evaluate_read(
    *,
    task_id: str,
    path: str,
    resolved_path: str,
    offset: int,
    limit: int,
    complete_coverage: bool = False,
    broad_read_reason: str | None = None,
) -> dict[str, Any]:
    """Return retrieval decision for a read_file call."""

    cfg = load_retrieval_config()
    file_size = 0
    try:
        file_size = os.path.getsize(resolved_path)
    except OSError:
        pass
    estimated_tokens = _estimate_tokens_from_bytes(file_size) if file_size else 0
    broad_reasons: list[str] = []
    if limit > cfg.broad_read_line_threshold:
        broad_reasons.append(
            f"requested {limit} lines > threshold {cfg.broad_read_line_threshold}"
        )
    if file_size > cfg.broad_read_byte_threshold and limit > cfg.broad_read_line_threshold:
        broad_reasons.append(
            f"file size {file_size} bytes > threshold {cfg.broad_read_byte_threshold}"
        )
    if estimated_tokens > cfg.broad_read_token_threshold and limit > cfg.broad_read_line_threshold:
        broad_reasons.append(
            f"estimated {estimated_tokens} tokens > threshold {cfg.broad_read_token_threshold}"
        )

    if not broad_reasons:
        return {"allowed": True, "broad": False, "mode": cfg.mode}

    locator_present = has_locator_history(task_id)
    reason_present = bool((broad_read_reason or "").strip())
    if cfg.mode == "disciplined" and not locator_present and not complete_coverage and not reason_present:
        return {
            "allowed": False,
            "broad": True,
            "mode": cfg.mode,
            "path": path,
            "resolved_path": resolved_path,
            "offset": offset,
            "limit": limit,
            "broad_reasons": broad_reasons,
            "message": (
                "Vesta retrieval policy blocked an unjustified broad read. "
                "Use search_files/manifest/counts first, set complete_coverage "
                "for whole-document work, or provide broad_read_reason."
            ),
        }

    if cfg.mode == "permissive":
        _record_broad_read(
            path=path,
            offset=offset,
            limit=limit,
            mode=cfg.mode,
            broad_reasons=broad_reasons,
            broad_read_reason=broad_read_reason or "permissive broad read",
        )

    return {
        "allowed": True,
        "broad": True,
        "mode": cfg.mode,
        "locator_present": locator_present,
        "complete_coverage": complete_coverage,
        "broad_read_reason": broad_read_reason or "",
        "broad_reasons": broad_reasons,
    }


def _record_broad_read(
    *,
    path: str,
    offset: int,
    limit: int,
    mode: str,
    broad_reasons: list[str],
    broad_read_reason: str,
) -> None:
    try:
        from vesta_runtime import append_ledger_entry

        append_ledger_entry(
            entry_type="action",
            title="Broad read allowed",
            statement=(
                f"Broad read allowed in {mode} mode for {path} "
                f"offset={offset} limit={limit}. Reason: {broad_read_reason}"
            ),
            refs=[path],
            status="active",
            materiality="medium",
            structured_payload={
                "broad_reasons": broad_reasons,
                "mode": mode,
            },
            actor="runtime",
        )
    except Exception:
        pass
