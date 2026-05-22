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
DEFAULT_READ_FILE_LINE_LIMIT = 180
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


def build_retrieval_prompt_contract() -> str:
    """Return the stable prompt block for Vesta locator-first retrieval."""

    cfg = load_retrieval_config()
    if cfg.mode != "disciplined":
        return ""
    narrow_limit = min(DEFAULT_READ_FILE_LINE_LIMIT, cfg.broad_read_line_threshold)
    return (
        "Vesta retrieval discipline:\n"
        "- For unfamiliar source files, locate before reading with search_files or a manifest/count tool.\n"
        f"- Prefer narrow read_file windows, normally <= {narrow_limit} lines.\n"
        "- Do not broad-read by default; broad reads require complete_coverage=true or a short broad_read_reason.\n"
        "- When read_file says unchanged/BLOCKED for a duplicate region, use prior content, another window, or record a gap.\n"
        "- Do not chase exhaustive coverage unless requested; synthesize once evidence is adequate and record gaps.\n"
        "- Use typed Vesta/file tools directly; do not bypass them through terminal or execute_code."
    )


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
    matched_paths: list[str] | None = None,
) -> None:
    """Record a search/manifest action as locator history for a task."""

    coerced_count = result_count
    if coerced_count is not None:
        try:
            coerced_count = int(coerced_count)
        except (TypeError, ValueError):
            coerced_count = None
    entry = {
        "pattern": pattern,
        "target": target,
        "path": path,
        "result_count": coerced_count,
        "matched_paths": list(dict.fromkeys(matched_paths or []))[:50],
    }
    with _LOCATOR_LOCK:
        items = _LOCATOR_HISTORY.setdefault(task_id, [])
        items.append(entry)
        if len(items) > _MAX_LOCATORS_PER_TASK:
            del items[:-_MAX_LOCATORS_PER_TASK]


def has_locator_history(task_id: str) -> bool:
    with _LOCATOR_LOCK:
        return bool(_LOCATOR_HISTORY.get(task_id))


def _locator_has_positive_results(locator: dict[str, Any]) -> bool:
    count = locator.get("result_count")
    if isinstance(count, int):
        return count > 0
    return bool(locator.get("matched_paths"))


def _resolve_locator_match(match_path: str, locator: dict[str, Any]) -> Path:
    candidate = Path(match_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve(strict=False)
    root_raw = str(locator.get("path") or "")
    root = Path(root_raw).expanduser() if root_raw else Path.cwd()
    if root.is_absolute():
        try:
            base = root if root.is_dir() else root.parent
        except OSError:
            base = root.parent
    else:
        base = Path.cwd()
    return (base / candidate).resolve(strict=False)


def _locator_matches_read_path(locator: dict[str, Any], resolved_path: str) -> str | None:
    read_path = Path(resolved_path).expanduser().resolve(strict=False)
    for match in locator.get("matched_paths") or []:
        if not match:
            continue
        candidate = _resolve_locator_match(str(match), locator)
        if candidate == read_path:
            return str(match)
    return None


def relevant_locator_for_path(task_id: str, resolved_path: str) -> dict[str, Any] | None:
    with _LOCATOR_LOCK:
        locators = list(_LOCATOR_HISTORY.get(task_id, []))
    for locator in reversed(locators):
        if not _locator_has_positive_results(locator):
            continue
        matched_path = _locator_matches_read_path(locator, resolved_path)
        if matched_path is not None:
            result = dict(locator)
            result["matched_path"] = matched_path
            return result
    return None


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

    locator = relevant_locator_for_path(task_id, resolved_path)
    locator_present = locator is not None
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
        allow_reason = broad_read_reason or "permissive broad read"
    elif complete_coverage:
        allow_reason = broad_read_reason or "complete coverage requested"
    elif reason_present:
        allow_reason = broad_read_reason or "explicit broad read reason"
    else:
        allow_reason = "relevant locator-first evidence present"

    _record_broad_read(
        path=path,
        offset=offset,
        limit=limit,
        mode=cfg.mode,
        broad_reasons=broad_reasons,
        broad_read_reason=allow_reason,
        locator=locator,
    )

    return {
        "allowed": True,
        "broad": True,
        "mode": cfg.mode,
        "locator_present": locator_present,
        "locator": _public_locator(locator),
        "complete_coverage": complete_coverage,
        "broad_read_reason": broad_read_reason or "",
        "broad_reasons": broad_reasons,
    }


def _public_locator(locator: dict[str, Any] | None) -> dict[str, Any] | None:
    if not locator:
        return None
    return {
        "pattern": locator.get("pattern", ""),
        "target": locator.get("target", ""),
        "path": locator.get("path", ""),
        "result_count": locator.get("result_count"),
        "matched_path": locator.get("matched_path", ""),
    }


def _record_broad_read(
    *,
    path: str,
    offset: int,
    limit: int,
    mode: str,
    broad_reasons: list[str],
    broad_read_reason: str,
    locator: dict[str, Any] | None = None,
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
            refs=[path, *(([str(locator.get("matched_path", ""))] if locator else []))],
            status="active",
            materiality="medium",
            structured_payload={
                "broad_reasons": broad_reasons,
                "mode": mode,
                "locator": _public_locator(locator),
            },
            actor="runtime",
        )
    except Exception:
        pass
