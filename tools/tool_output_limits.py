"""Configurable tool-output truncation limits.

Ported from anomalyco/opencode PR #23770 (``feat(truncate): allow
configuring tool output truncation limits``).

OpenCode hardcoded ``MAX_LINES = 2000`` and ``MAX_BYTES = 50 * 1024``
as tool-output truncation thresholds. Hermes-agent had the same
hardcoded constants in two places:

* ``tools/terminal_tool.py`` — ``MAX_OUTPUT_CHARS = 50000`` (terminal
  stdout/stderr cap)
* ``tools/file_operations.py`` — ``MAX_LINES = 2000`` /
  ``MAX_LINE_LENGTH = 2000`` (read_file pagination cap + per-line cap)

This module centralises those values behind a single config section
(``tool_output`` in ``config.yaml``) so power users can tune them
without patching the source. The existing hardcoded numbers remain as
defaults, so behaviour is unchanged when the config key is absent.

Example ``config.yaml``::

    tool_output:
      max_bytes: 100000        # terminal output cap (chars)
      max_lines: 5000          # read_file pagination + truncation cap
      max_line_length: 2000    # per-line length cap before '... [truncated]'

The limits reader is defensive: any error (missing config file, invalid
value type, etc.) falls back to the built-in defaults so tools never
fail because of a malformed config.
"""

from __future__ import annotations

import os
from typing import Any, Dict

# Hardcoded defaults — these match the pre-existing values, so adding
# this module is behaviour-preserving for users who don't set
# ``tool_output`` in config.yaml.
DEFAULT_MAX_BYTES = 50_000       # terminal_tool.MAX_OUTPUT_CHARS
DEFAULT_MAX_LINES = 2000         # file_operations.MAX_LINES
DEFAULT_MAX_LINE_LENGTH = 2000   # file_operations.MAX_LINE_LENGTH
VESTA_CONTEXT_CAP_DIVISOR = 8
VESTA_CONTEXT_CAP_FLOOR = 4_000
VESTA_CHECKPOINT_RETRIEVAL_LIMIT = 12
_VESTA_EVIDENCE_COUNT_BY_RUN: dict[str, int] = {}
_VESTA_ARTIFACT_PROGRESS_BY_RUN: dict[str, str] = {}


def _coerce_positive_int(value: Any, default: int) -> int:
    """Return ``value`` as a positive int, or ``default`` on any issue."""
    try:
        iv = int(value)
    except (TypeError, ValueError):
        return default
    if iv <= 0:
        return default
    return iv


def get_tool_output_limits() -> Dict[str, int]:
    """Return resolved tool-output limits, reading ``tool_output`` from config.

    Keys: ``max_bytes``, ``max_lines``, ``max_line_length``. Missing or
    invalid entries fall through to the ``DEFAULT_*`` constants. This
    function NEVER raises.
    """
    try:
        from hermes_cli.config import load_config
        cfg = load_config() or {}
        section = cfg.get("tool_output") if isinstance(cfg, dict) else None
        if not isinstance(section, dict):
            section = {}
    except Exception:
        section = {}

    return {
        "max_bytes": _coerce_positive_int(section.get("max_bytes"), DEFAULT_MAX_BYTES),
        "max_lines": _coerce_positive_int(section.get("max_lines"), DEFAULT_MAX_LINES),
        "max_line_length": _coerce_positive_int(
            section.get("max_line_length"), DEFAULT_MAX_LINE_LENGTH
        ),
    }


def get_max_bytes() -> int:
    """Shortcut for terminal-tool callers that only need the byte cap."""
    return get_tool_output_limits()["max_bytes"]


def get_vesta_context_length_tokens() -> int | None:
    """Return the active Vesta model context length, when the run exported it."""
    raw = (
        os.environ.get("VESTA_CONTEXT_LENGTH_TOKENS")
        or os.environ.get("HERMES_MODEL_CONTEXT_LENGTH_TOKENS")
    )
    if not raw:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def apply_vesta_context_byte_cap(limit: int) -> tuple[int, bool, int | None]:
    """Tighten one-call evidence output caps for small-context local models.

    The config-level Vesta retrieval cap is still the primary knob. This helper
    only lowers it when the active model context would make repeated broad
    retrieval payloads likely to trigger compression loops.
    """
    context_length = get_vesta_context_length_tokens()
    if not context_length:
        return limit, False, None
    context_cap = max(VESTA_CONTEXT_CAP_FLOOR, context_length // VESTA_CONTEXT_CAP_DIVISOR)
    capped = min(limit, context_cap)
    return capped, capped < limit, context_length


def get_vesta_retrieval_output_limit_info(
    configured: int,
    *,
    source: str,
) -> Dict[str, Any]:
    """Return a Vesta disciplined output cap for any text-returning tool."""
    info: Dict[str, Any] = {
        "max_bytes": configured,
        "source": source,
        "vesta_active": False,
        "disciplined": False,
    }
    try:
        from vesta_runtime import get_current_run

        if get_current_run() is None:
            return info
        info["vesta_active"] = True
    except Exception:
        return info

    try:
        from hermes_cli.config import load_config

        cfg = load_config() or {}
        vesta = cfg.get("vesta", {}) if isinstance(cfg, dict) else {}
        retrieval = vesta.get("retrieval", {}) if isinstance(vesta, dict) else {}
        if not isinstance(retrieval, dict):
            return info
        if str(retrieval.get("mode", "disciplined")).strip().lower() != "disciplined":
            return info
        threshold = _coerce_positive_int(
            retrieval.get("broad_read_byte_threshold"),
            configured,
        )
    except Exception:
        return info

    capped = min(configured, threshold)
    capped, context_capped, context_length = apply_vesta_context_byte_cap(capped)
    info["disciplined"] = True
    info["max_bytes"] = capped
    if info["max_bytes"] < configured:
        info["source"] = "vesta_retrieval"
    if context_capped:
        info["source"] = "vesta_context_retrieval"
        info["context_length_tokens"] = context_length
    return info


def _current_vesta_run() -> Any | None:
    try:
        from vesta_runtime import get_current_run

        return get_current_run()
    except Exception:
        return None


def _vesta_run_key(run: Any) -> str:
    run_dir = getattr(run, "run_dir", None)
    if run_dir:
        return str(run_dir)
    return str(id(run))


def _vesta_artifact_checkpoint_fingerprint(run: Any) -> str | None:
    try:
        manifest_path = getattr(run, "artifact_manifest_path", None)
        if not manifest_path:
            return None
        text = manifest_path.read_text(encoding="utf-8")
        stat = manifest_path.stat()
    except Exception:
        return None
    if "Expected By: `research_artifact_section_write`" not in text:
        return None
    return f"{stat.st_mtime_ns}:{len(text)}"


def note_vesta_runtime_progress(kind: str = "progress") -> None:
    """Reset evidence-retrieval pressure after durable Vesta progress."""
    run = _current_vesta_run()
    if run is None:
        return
    key = _vesta_run_key(run)
    _VESTA_EVIDENCE_COUNT_BY_RUN.pop(key, None)
    fingerprint = _vesta_artifact_checkpoint_fingerprint(run)
    if fingerprint:
        _VESTA_ARTIFACT_PROGRESS_BY_RUN[key] = fingerprint


def note_vesta_artifact_checkpoint() -> None:
    """Reset the evidence-retrieval pressure counter after an artifact write."""
    note_vesta_runtime_progress("artifact")


def vesta_evidence_checkpoint_notice(source: str) -> Dict[str, Any] | None:
    """Return a compact notice when evidence retrieval outruns checkpointing."""
    run = _current_vesta_run()
    if run is None:
        return None
    try:
        from hermes_cli.config import load_config

        cfg = load_config() or {}
        vesta = cfg.get("vesta", {}) if isinstance(cfg, dict) else {}
        retrieval = vesta.get("retrieval", {}) if isinstance(vesta, dict) else {}
        if not isinstance(retrieval, dict):
            return None
        if str(retrieval.get("mode", "disciplined")).strip().lower() != "disciplined":
            return None
    except Exception:
        return None

    key = _vesta_run_key(run)
    artifact_fingerprint = _vesta_artifact_checkpoint_fingerprint(run)
    if artifact_fingerprint and _VESTA_ARTIFACT_PROGRESS_BY_RUN.get(key) != artifact_fingerprint:
        _VESTA_ARTIFACT_PROGRESS_BY_RUN[key] = artifact_fingerprint
        _VESTA_EVIDENCE_COUNT_BY_RUN.pop(key, None)
        return None

    count = _VESTA_EVIDENCE_COUNT_BY_RUN.get(key, 0) + 1
    _VESTA_EVIDENCE_COUNT_BY_RUN[key] = count
    if count <= VESTA_CHECKPOINT_RETRIEVAL_LIMIT:
        return None

    return {
        "vesta_checkpoint_required": True,
        "source": source,
        "evidence_calls_since_checkpoint": count,
        "evidence_call_limit": VESTA_CHECKPOINT_RETRIEVAL_LIMIT,
        "repair_hint": (
            "This Vesta run has gathered many evidence payloads without a "
            "compact durable checkpoint or compact artifact checkpoint. "
            "Write a bounded section with "
            "research_artifact_section_write (the current typed evidence "
            "artifact writer), append a high-signal ledger checkpoint, or "
            "record explicit gaps/coverage before requesting more broad evidence."
        ),
    }


def get_terminal_max_bytes() -> int:
    """Return only the effective terminal byte cap."""
    return int(get_terminal_output_limit_info()["max_bytes"])


def get_terminal_output_limit_info() -> Dict[str, Any]:
    """Return the terminal output cap, tightened during active Vesta runs.

    The generic ``tool_output.max_bytes`` default stays broad for build logs and
    ordinary CLI work. Vesta's disciplined retrieval mode treats large terminal
    payloads as evidence retrieval, so it should honor the smaller Vesta byte
    threshold when a Vesta run is actually bound to the current context.
    """
    configured = get_max_bytes()
    info: Dict[str, Any] = {
        "max_bytes": configured,
        "source": "tool_output",
        "vesta_active": False,
        "disciplined": False,
    }
    try:
        from vesta_runtime import get_current_run

        if get_current_run() is None:
            return info
        info["vesta_active"] = True
    except Exception:
        return info

    try:
        from hermes_cli.config import load_config

        cfg = load_config() or {}
        vesta = cfg.get("vesta", {}) if isinstance(cfg, dict) else {}
        retrieval = vesta.get("retrieval", {}) if isinstance(vesta, dict) else {}
        if not isinstance(retrieval, dict):
            return info
        if str(retrieval.get("mode", "disciplined")).strip().lower() != "disciplined":
            return info
        info["disciplined"] = True
        threshold = _coerce_positive_int(
            retrieval.get("broad_read_byte_threshold"),
            configured,
        )
    except Exception:
        return info
    capped = min(configured, threshold)
    capped, context_capped, context_length = apply_vesta_context_byte_cap(capped)
    info["max_bytes"] = capped
    if info["max_bytes"] < configured:
        info["source"] = "vesta_retrieval"
    if context_capped:
        info["source"] = "vesta_context_retrieval"
        info["context_length_tokens"] = context_length
    return info


def get_max_lines() -> int:
    """Shortcut for file-ops callers that only need the line cap."""
    return get_tool_output_limits()["max_lines"]


def get_max_line_length() -> int:
    """Shortcut for file-ops callers that only need the per-line cap."""
    return get_tool_output_limits()["max_line_length"]
