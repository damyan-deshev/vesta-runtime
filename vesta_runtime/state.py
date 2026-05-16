"""File-backed Vesta run state.

This module deliberately avoids becoming a database. The model-facing runtime
surface is Markdown, with small helper functions that own ids, timestamps, and
run/session metadata.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import hashlib
import json
import os
import re
import threading
import uuid

from hermes_constants import get_hermes_home
from hermes_time import now as hermes_now


_CURRENT_RUN: ContextVar["VestaRun | None"] = ContextVar("vesta_current_run", default=None)
_STATE_LOCK = threading.RLock()

VALID_LEDGER_ENTRY_TYPES = {
    "claim",
    "decision",
    "action",
    "gap",
    "contradiction",
    "commitment",
    "artifact",
    "worker_state",
    "checkpoint",
    "next_step",
    "failure",
    "source_ref",
    "raw_ref",
    "verification",
    "document_chunk_finding",
    "document_recap",
}

VALID_MATERIALITY = {"low", "medium", "high", "critical"}


@dataclass(frozen=True)
class VestaRun:
    """Resolved Vesta run paths and identity."""

    run_id: str
    workspace_hash: str
    workspace_path: str
    run_dir: Path
    run_md_path: Path
    ledger_path: Path
    resume_packet_path: Path
    artifact_manifest_path: Path
    finalization_path: Path
    worker_state_path: Path
    validator_result_path: Path
    control_plane_path: Path
    handoff_path: Path
    raw_dir: Path
    raw_index_path: Path
    created_at: str


def _timestamp() -> str:
    return hermes_now().isoformat()


def _slug(value: str, *, max_len: int = 48) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-._")
    if not cleaned:
        cleaned = "workspace"
    return cleaned[:max_len]


def _workspace_path(workspace_path: str | os.PathLike[str] | None = None) -> str:
    raw = (
        str(workspace_path)
        if workspace_path is not None
        else os.getenv("TERMINAL_CWD") or os.getcwd()
    )
    return str(Path(raw).expanduser().resolve())


def _workspace_hash(workspace_path: str) -> str:
    digest = hashlib.sha256(workspace_path.encode("utf-8")).hexdigest()[:16]
    return f"{_slug(Path(workspace_path).name)}-{digest}"


def _new_run_id() -> str:
    ts = hermes_now().strftime("%Y%m%d_%H%M%S")
    return f"run_{ts}_{uuid.uuid4().hex[:6]}"


def _write_if_missing(path: Path, content: str) -> None:
    if path.exists():
        return
    path.write_text(content, encoding="utf-8")


def _set_env_for_run(run: VestaRun) -> None:
    os.environ["VESTA_RUN_ID"] = run.run_id
    os.environ["VESTA_RUN_DIR"] = str(run.run_dir)
    os.environ["VESTA_LEDGER_PATH"] = str(run.ledger_path)


def set_current_run(run: VestaRun | None) -> None:
    """Set the current run for this execution context."""

    _CURRENT_RUN.set(run)
    if run is not None:
        _set_env_for_run(run)
    else:
        for key in ("VESTA_RUN_ID", "VESTA_RUN_DIR", "VESTA_LEDGER_PATH"):
            os.environ.pop(key, None)


def get_current_run() -> VestaRun | None:
    """Return the active Vesta run, if one is bound."""

    return _CURRENT_RUN.get()


def _run_from_env() -> VestaRun | None:
    run_id = os.getenv("VESTA_RUN_ID")
    run_dir_raw = os.getenv("VESTA_RUN_DIR")
    ledger_raw = os.getenv("VESTA_LEDGER_PATH")
    if not run_id or not run_dir_raw:
        return None
    run_dir = Path(run_dir_raw)
    ledger_path = Path(ledger_raw) if ledger_raw else run_dir / "ledger.md"
    workspace_path = os.getenv("VESTA_WORKSPACE_PATH") or ""
    workspace_hash = os.getenv("VESTA_WORKSPACE_HASH") or ""
    run = VestaRun(
        run_id=run_id,
        workspace_hash=workspace_hash,
        workspace_path=workspace_path,
        run_dir=run_dir,
        run_md_path=run_dir / "run.md",
        ledger_path=ledger_path,
        resume_packet_path=run_dir / "resume-packet.md",
        artifact_manifest_path=run_dir / "artifact-manifest.md",
        finalization_path=run_dir / "finalization.md",
        worker_state_path=run_dir / "worker-state.md",
        validator_result_path=run_dir / "validator-result.md",
        control_plane_path=run_dir / "control-plane.md",
        handoff_path=run_dir / "handoff.md",
        raw_dir=run_dir / "raw",
        raw_index_path=run_dir / "raw" / "index.md",
        created_at="",
    )
    if run.run_dir.exists():
        set_current_run(run)
        return run
    return None


def create_run(
    *,
    session_id: str,
    parent_session_id: str | None = None,
    task_id: str | None = None,
    workspace_path: str | os.PathLike[str] | None = None,
    model: str | None = None,
    provider: str | None = None,
    platform: str | None = None,
    run_id: str | None = None,
) -> VestaRun:
    """Create and bind a Vesta run with eager Markdown seed files."""

    resolved_workspace = _workspace_path(workspace_path)
    workspace_hash = _workspace_hash(resolved_workspace)
    created_at = _timestamp()
    rid = run_id or _new_run_id()
    run_dir = get_hermes_home() / "vesta" / "workspaces" / workspace_hash / "runs" / rid
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    run = VestaRun(
        run_id=rid,
        workspace_hash=workspace_hash,
        workspace_path=resolved_workspace,
        run_dir=run_dir,
        run_md_path=run_dir / "run.md",
        ledger_path=run_dir / "ledger.md",
        resume_packet_path=run_dir / "resume-packet.md",
        artifact_manifest_path=run_dir / "artifact-manifest.md",
        finalization_path=run_dir / "finalization.md",
        worker_state_path=run_dir / "worker-state.md",
        validator_result_path=run_dir / "validator-result.md",
        control_plane_path=run_dir / "control-plane.md",
        handoff_path=run_dir / "handoff.md",
        raw_dir=raw_dir,
        raw_index_path=raw_dir / "index.md",
        created_at=created_at,
    )

    _write_if_missing(run.run_md_path, _render_run_seed(
        run=run,
        session_id=session_id,
        parent_session_id=parent_session_id,
        task_id=task_id,
        model=model,
        provider=provider,
        platform=platform,
    ))
    _write_if_missing(run.ledger_path, _render_ledger_seed(run, session_id=session_id))
    _write_if_missing(run.raw_index_path, _render_raw_index_seed(run))
    _write_if_missing(run.artifact_manifest_path, _render_artifact_manifest_seed(run))
    _write_if_missing(run.worker_state_path, _render_worker_state_seed(run))
    _write_if_missing(run.validator_result_path, _render_validator_result_seed(run))
    _write_if_missing(run.control_plane_path, _render_control_plane_seed(run))
    _write_if_missing(run.handoff_path, _render_handoff_seed(run))

    os.environ["VESTA_WORKSPACE_PATH"] = run.workspace_path
    os.environ["VESTA_WORKSPACE_HASH"] = run.workspace_hash
    set_current_run(run)
    return run


def ensure_current_run(*, session_id: str | None = None) -> VestaRun:
    """Return active run or create a minimal one when a Hermes session exists."""

    run = get_current_run() or _run_from_env()
    if run is not None:
        return run
    sid = session_id or os.getenv("HERMES_SESSION_ID")
    if not sid:
        raise RuntimeError("No active Vesta run or Hermes session is available")
    return create_run(session_id=sid)


def _render_run_seed(
    *,
    run: VestaRun,
    session_id: str,
    parent_session_id: str | None,
    task_id: str | None,
    model: str | None,
    provider: str | None,
    platform: str | None,
) -> str:
    parent = parent_session_id or ""
    lineage = f"- {session_id}"
    if parent:
        lineage = f"- {parent}\n- {session_id}"
    return f"""# Vesta Run

Run ID: `{run.run_id}`
Created At: `{run.created_at}`
Workspace Hash: `{run.workspace_hash}`
Workspace Path: `{run.workspace_path}`
Hermes Session ID: `{session_id}`
Hermes Parent Session ID: `{parent}`
Task ID: `{task_id or ''}`
Model: `{model or ''}`
Provider: `{provider or ''}`
Platform: `{platform or ''}`

## Hermes Session Lineage

{lineage}

## Prompt / Cache Contract

- Vesta state is file-backed.
- Runtime policy should not mutate system prompt or tool surface mid-run.

## Artifacts

- Ledger: `{run.ledger_path}`
- Resume packet: `{run.resume_packet_path}`
- Artifact manifest: `{run.artifact_manifest_path}`
- Finalization: `{run.finalization_path}`
- Worker state: `{run.worker_state_path}`
- Validator result: `{run.validator_result_path}`
- Control plane snapshot: `{run.control_plane_path}`
- Handoff: `{run.handoff_path}`
- Raw index: `{run.raw_index_path}`

{_render_vesta_effective_config_section()}
"""


def _render_ledger_seed(run: VestaRun, *, session_id: str) -> str:
    return f"""# Vesta Ledger

Run ID: `{run.run_id}`
Hermes Session ID: `{session_id}`
Created At: `{run.created_at}`

## Objective

- unresolved

## Decisions

## Claims

## Actions

## Gaps

## Contradictions

## Commitments

## Artifacts

## Workers

## Checkpoints

## Failures

## Next Action

- unresolved

## Entries
"""


def _render_raw_index_seed(run: VestaRun) -> str:
    return f"""# Vesta Raw Output Index

Run ID: `{run.run_id}`
Created At: `{run.created_at}`

## Entries
"""


def _active_vesta_config() -> dict[str, Any]:
    defaults = {
        "retrieval": {
            "mode": "disciplined",
            "broad_read_line_threshold": 200,
            "broad_read_byte_threshold": 20_000,
            "broad_read_token_threshold": 12_000,
        },
        "whole_document": {
            "token_threshold": 100_000,
            "max_chunk_tokens": 20_000,
        },
        "raw_retention": {
            "retain_by_default": True,
            "purge_preserves_manifest": True,
        },
    }
    try:
        from hermes_cli.config import load_config

        cfg = load_config().get("vesta", {})
        if isinstance(cfg, dict):
            merged = json.loads(json.dumps(defaults))
            for section, values in cfg.items():
                if isinstance(values, dict) and isinstance(merged.get(section), dict):
                    merged[section].update(values)
                else:
                    merged[section] = values
            return merged
    except Exception:
        pass
    return defaults


def _render_vesta_effective_config_section() -> str:
    cfg = _active_vesta_config()
    retrieval = cfg.get("retrieval", {})
    whole_document = cfg.get("whole_document", {})
    raw_retention = cfg.get("raw_retention", {})
    return f"""## Vesta Effective Config

- Retrieval Mode: `{retrieval.get('mode', 'disciplined')}`
- Broad Read Line Threshold: `{retrieval.get('broad_read_line_threshold', 200)}`
- Broad Read Byte Threshold: `{retrieval.get('broad_read_byte_threshold', 20_000)}`
- Broad Read Token Threshold: `{retrieval.get('broad_read_token_threshold', 12_000)}`
- Whole Document Token Threshold: `{whole_document.get('token_threshold', 100_000)}`
- Whole Document Max Chunk Tokens: `{whole_document.get('max_chunk_tokens', 20_000)}`
- Raw Retention Retain By Default: `{raw_retention.get('retain_by_default', True)}`
- Raw Retention Purge Preserves Manifest: `{raw_retention.get('purge_preserves_manifest', True)}`

## Prompt Cache Contract

- Runtime prompt/tool surface should remain stable within a run.
- Config changes are captured as run metadata, not injected as ad hoc prompt
  changes mid-session.
"""


def _render_artifact_manifest_seed(run: VestaRun) -> str:
    return f"""# Vesta Artifact Manifest

Run ID: `{run.run_id}`
Created At: `{run.created_at}`

## Entries
"""


def _render_worker_state_seed(run: VestaRun) -> str:
    return f"""# Vesta Worker State

Run ID: `{run.run_id}`
Created At: `{run.created_at}`

## Entries
"""


def _render_validator_result_seed(run: VestaRun) -> str:
    return f"""# Vesta Validator Result

Run ID: `{run.run_id}`
Created At: `{run.created_at}`

## Status

- Validator Status: `absent`

## Entries
"""


def _render_control_plane_seed(run: VestaRun) -> str:
    return f"""# Vesta Control Plane Snapshot

Run ID: `{run.run_id}`
Created At: `{run.created_at}`
Source Of Truth: Vesta artifact files in `{run.run_dir}`

## Status

- Snapshot Status: `not_generated`
"""


def _render_handoff_seed(run: VestaRun) -> str:
    return f"""# Vesta Handoff

Run ID: `{run.run_id}`
Created At: `{run.created_at}`

## Status

- Handoff Status: `not_generated`
"""


def _json_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def append_ledger_entry(
    *,
    entry_type: str,
    title: str,
    statement: str,
    refs: list[str] | None = None,
    status: str = "active",
    materiality: str = "medium",
    next_action: str | None = None,
    structured_payload: dict[str, Any] | None = None,
    session_id: str | None = None,
    actor: str = "agent",
) -> dict[str, Any]:
    """Append one small model-facing ledger entry."""

    run = ensure_current_run(session_id=session_id)
    if entry_type not in VALID_LEDGER_ENTRY_TYPES:
        raise ValueError(f"Unsupported ledger entry_type: {entry_type}")
    if materiality not in VALID_MATERIALITY:
        raise ValueError(f"Unsupported materiality: {materiality}")
    if not title.strip():
        raise ValueError("Ledger title is required")
    if not statement.strip():
        raise ValueError("Ledger statement is required")

    entry_id = f"le_{uuid.uuid4().hex[:10]}"
    timestamp = _timestamp()
    sid = session_id or os.getenv("HERMES_SESSION_ID") or ""
    refs = refs or []
    payload = structured_payload or {}

    lines = [
        "",
        f"### {entry_id} - {title.strip()}",
        "",
        f"- Timestamp: `{timestamp}`",
        f"- Type: `{entry_type}`",
        f"- Status: `{status}`",
        f"- Materiality: `{materiality}`",
        f"- Actor: `{actor}`",
        f"- Run ID: `{run.run_id}`",
        f"- Hermes Session ID: `{sid}`",
        f"- Statement: {statement.strip()}",
    ]
    if refs:
        lines.append(f"- Refs: {', '.join(f'`{ref}`' for ref in refs)}")
    if next_action:
        lines.append(f"- Next Action: {next_action.strip()}")
    if payload:
        lines.append(f"- Structured Payload: `{_json_compact(payload)}`")
    lines.append("")

    with _STATE_LOCK:
        with run.ledger_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines))

    return {
        "entry_id": entry_id,
        "run_id": run.run_id,
        "ledger_path": str(run.ledger_path),
        "timestamp": timestamp,
    }


def record_session_rotation(*, old_session_id: str, new_session_id: str, reason: str) -> None:
    """Record Hermes session lineage changes inside the active Vesta run."""

    run = ensure_current_run(session_id=new_session_id)
    timestamp = _timestamp()
    with _STATE_LOCK:
        with run.run_md_path.open("a", encoding="utf-8") as f:
            f.write(
                "\n## Hermes Session Rotation\n\n"
                f"- Timestamp: `{timestamp}`\n"
                f"- Reason: `{reason}`\n"
                f"- Old Session ID: `{old_session_id}`\n"
                f"- New Session ID: `{new_session_id}`\n"
            )
    append_ledger_entry(
        entry_type="checkpoint",
        title="Hermes session rotated",
        statement=f"Hermes session rotated from {old_session_id} to {new_session_id}.",
        refs=[str(run.run_md_path)],
        status="active",
        materiality="high",
        next_action="Consult ledger and resume packet before material continuation.",
        session_id=new_session_id,
        actor="runtime",
        structured_payload={"reason": reason, "old_session_id": old_session_id, "new_session_id": new_session_id},
    )
    write_resume_packet(
        session_id=new_session_id,
        current_phase="post-compression",
        next_action="Consult ledger and continue active work.",
        reason=reason,
    )


def write_resume_packet(
    *,
    session_id: str | None = None,
    objective: str | None = None,
    current_phase: str = "active",
    next_action: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Write a compact resume packet from durable run state."""

    run = ensure_current_run(session_id=session_id)
    timestamp = _timestamp()
    ledger_excerpt = ""
    try:
        ledger_text = run.ledger_path.read_text(encoding="utf-8")
        ledger_excerpt = ledger_text[-4_000:]
    except OSError:
        ledger_excerpt = ""

    resolved_next_action = (next_action or "").strip() or "Consult ledger and continue active work."
    resolved_objective = (objective or "").strip() or "See ledger Objective section."
    sid = session_id or os.getenv("HERMES_SESSION_ID") or ""

    content = f"""# Vesta Resume Packet

Run ID: `{run.run_id}`
Generated At: `{timestamp}`
Reason: `{reason or ''}`
Hermes Session ID: `{sid}`
Ledger Path: `{run.ledger_path}`

## Objective

{resolved_objective}

## Current Phase

{current_phase}

## Active Working State

- Commitments: see `ledger.md` Commitments and Entries sections.
- Decisions: see `ledger.md` Decisions and Entries sections.
- Verified Claims: see `ledger.md` Claims and Entries sections.
- Open Gaps: see `ledger.md` Gaps and Entries sections.
- Contradictions: see `ledger.md` Contradictions and Entries sections.
- Worker Status: see `ledger.md` Workers and Entries sections.
- Artifact Manifest: see run artifacts and ledger Artifact entries.

## Next Action

{resolved_next_action}

## Recent Ledger Excerpt

```markdown
{ledger_excerpt}
```
"""
    with _STATE_LOCK:
        run.resume_packet_path.write_text(content, encoding="utf-8")
    return {
        "run_id": run.run_id,
        "resume_packet_path": str(run.resume_packet_path),
        "next_action": resolved_next_action,
        "generated_at": timestamp,
    }


def capture_raw_output(
    *,
    content: str,
    source: str,
    tool_use_id: str,
    excerpt_chars: int = 1500,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist raw output under the current run and index it."""

    run = ensure_current_run(session_id=session_id)
    safe_id = _slug(tool_use_id or uuid.uuid4().hex[:8], max_len=80)
    if not safe_id:
        safe_id = uuid.uuid4().hex[:8]
    raw_path = run.raw_dir / f"{safe_id}.txt"
    suffix = 1
    while raw_path.exists():
        raw_path = run.raw_dir / f"{safe_id}_{suffix}.txt"
        suffix += 1

    digest = hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()
    excerpt = content[:excerpt_chars]
    captured_at = _timestamp()
    rel = raw_path.relative_to(run.run_dir)
    meta = metadata or {}

    with _STATE_LOCK:
        raw_path.write_text(content, encoding="utf-8", errors="replace")
        with run.raw_index_path.open("a", encoding="utf-8") as f:
            f.write(
                "\n### "
                f"{rel}\n\n"
                f"- Captured At: `{captured_at}`\n"
                f"- Source: `{source}`\n"
                f"- Tool Use ID: `{tool_use_id}`\n"
                f"- Size Chars: `{len(content)}`\n"
                f"- Hash: `sha256:{digest}`\n"
            )
            if meta:
                f.write(f"- Metadata: `{_json_compact(meta)}`\n")
            f.write("\n")

    return {
        "raw_ref": str(rel),
        "path": str(raw_path),
        "run_id": run.run_id,
        "hash": f"sha256:{digest}",
        "captured_at": captured_at,
        "excerpt": excerpt,
        "size_chars": len(content),
    }


def purge_raw_ref(
    *,
    raw_ref: str,
    reason: str = "",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Delete a raw payload while preserving the visible raw ref manifest."""

    run = ensure_current_run(session_id=session_id)
    if not raw_ref.strip():
        raise ValueError("raw_ref is required")
    rel = Path(raw_ref)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("raw_ref must be a relative run raw path")
    raw_path = run.run_dir / rel
    if not _path_is_within_run(raw_path, run):
        raise ValueError("raw_ref must stay inside the active run directory")

    timestamp = _timestamp()
    existed = raw_path.exists()
    status = "purged" if existed else "missing"
    with _STATE_LOCK:
        if existed:
            raw_path.unlink()
        with run.raw_index_path.open("a", encoding="utf-8") as f:
            f.write(
                "\n### "
                f"{raw_ref}\n\n"
                f"- Status: `{status}`\n"
                f"- Purged At: `{timestamp}`\n"
                f"- Reason: {reason}\n"
            )

    append_ledger_entry(
        entry_type="raw_ref",
        title=f"Raw ref {status}: {raw_ref}",
        statement=f"Raw ref `{raw_ref}` is `{status}`; manifest entry preserved.",
        refs=[raw_ref, str(run.raw_index_path)],
        status=status,
        materiality="medium",
        session_id=session_id,
        actor="runtime",
        structured_payload={"raw_ref": raw_ref, "reason": reason},
    )
    return {
        "raw_ref": raw_ref,
        "status": status,
        "raw_index_path": str(run.raw_index_path),
        "purged_at": timestamp,
    }


def _path_is_within_run(path: Path, run: VestaRun) -> bool:
    try:
        path.resolve(strict=False).relative_to(run.run_dir.resolve(strict=False))
        return True
    except ValueError:
        return False


ARTIFACT_STATUSES = {"expected", "exists", "missing", "superseded", "purged"}


def record_artifact(
    *,
    path: str,
    artifact_type: str,
    expected_by: str,
    status: str = "expected",
    impact_if_missing: str = "",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Append an artifact manifest entry and ledger artifact entry."""

    if status not in ARTIFACT_STATUSES:
        raise ValueError(f"Unsupported artifact status: {status}")
    run = ensure_current_run(session_id=session_id)
    artifact_id = f"art_{uuid.uuid4().hex[:10]}"
    timestamp = _timestamp()
    with _STATE_LOCK:
        with run.artifact_manifest_path.open("a", encoding="utf-8") as f:
            f.write(
                "\n### "
                f"{artifact_id}\n\n"
                f"- Path: `{path}`\n"
                f"- Type: `{artifact_type}`\n"
                f"- Expected By: `{expected_by}`\n"
                f"- Status: `{status}`\n"
                f"- Impact If Missing: {impact_if_missing}\n"
                f"- Recorded At: `{timestamp}`\n"
            )
    append_ledger_entry(
        entry_type="artifact",
        title=f"Artifact {status}: {path}",
        statement=f"Artifact `{path}` recorded with status `{status}`.",
        refs=[path, str(run.artifact_manifest_path)],
        status=status,
        materiality="high" if status in {"expected", "missing"} else "medium",
        session_id=session_id,
        actor="runtime",
        structured_payload={
            "artifact_id": artifact_id,
            "artifact_type": artifact_type,
            "expected_by": expected_by,
            "impact_if_missing": impact_if_missing,
        },
    )
    return {
        "artifact_id": artifact_id,
        "artifact_manifest_path": str(run.artifact_manifest_path),
        "status": status,
    }


WORKER_STATUSES = {
    "requested",
    "accepted",
    "running",
    "completed",
    "failed",
    "truncated",
    "cancelled",
}
PARENT_ACCEPTANCE_STATUSES = {"unreviewed", "accepted", "rejected", "needs_audit"}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _redact_secret_string(value: str) -> str:
    redacted = re.sub(
        r"(?i)\b(api[_-]?key|token|password|secret)\s*[:=]\s*[^,\s]+",
        lambda m: f"{m.group(1)}=<redacted>",
        value,
    )
    return re.sub(r"\bsk-[A-Za-z0-9_-]{8,}", "sk-<redacted>", redacted)


def _sanitize_runtime_payload(value: Any) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in ("api_key", "apikey", "token", "secret", "password")):
                clean[str(key)] = "<redacted>"
            else:
                clean[str(key)] = _sanitize_runtime_payload(item)
        return clean
    if isinstance(value, list):
        return [_sanitize_runtime_payload(item) for item in value]
    if isinstance(value, str):
        return _redact_secret_string(value)
    return value


def record_worker_state(
    *,
    worker_id: str,
    objective: str,
    status: str,
    model_lane: str,
    output_contract: dict[str, Any] | None = None,
    child_session_id: str = "",
    artifact_paths: list[str] | None = None,
    failures: list[str] | None = None,
    gaps: list[str] | None = None,
    material_claims: list[Any] | None = None,
    parent_acceptance: str = "unreviewed",
    spot_audit: str = "",
    next_action: str = "",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Append a durable worker state entry for parent acceptance/finalization."""

    if not worker_id.strip():
        raise ValueError("worker_id is required")
    if not objective.strip():
        raise ValueError("worker objective is required")
    if status not in WORKER_STATUSES:
        raise ValueError(f"Unsupported worker status: {status}")
    if not model_lane.strip():
        raise ValueError("model_lane is required")
    if parent_acceptance not in PARENT_ACCEPTANCE_STATUSES:
        raise ValueError(f"Unsupported parent_acceptance: {parent_acceptance}")

    run = ensure_current_run(session_id=session_id)
    timestamp = _timestamp()
    safe_payload = _sanitize_runtime_payload({
        "worker_id": worker_id.strip(),
        "parent_run_id": run.run_id,
        "child_session_id": child_session_id.strip(),
        "objective": objective.strip(),
        "output_contract": output_contract or {},
        "model_lane": model_lane.strip(),
        "status": status,
        "artifacts": artifact_paths or [],
        "failures": failures or [],
        "gaps": gaps or [],
        "material_claims": material_claims or [],
        "parent_acceptance": parent_acceptance,
        "spot_audit": spot_audit.strip(),
        "next_action": next_action.strip(),
        "recorded_at": timestamp,
    })

    with _STATE_LOCK:
        with run.worker_state_path.open("a", encoding="utf-8") as f:
            f.write(
                "\n### "
                f"{safe_payload['worker_id']} - {status}\n\n"
                f"- Recorded At: `{timestamp}`\n"
                f"- Parent Run ID: `{run.run_id}`\n"
                f"- Child Session ID: `{safe_payload['child_session_id']}`\n"
                f"- Objective: {safe_payload['objective']}\n"
                f"- Status: `{status}`\n"
                f"- Model Lane: `{safe_payload['model_lane']}`\n"
                f"- Parent Acceptance: `{parent_acceptance}`\n"
                f"- Artifacts: `{_json_compact(safe_payload['artifacts'])}`\n"
                f"- Failures: `{_json_compact(safe_payload['failures'])}`\n"
                f"- Gaps: `{_json_compact(safe_payload['gaps'])}`\n"
                f"- Material Claims: `{_json_compact(safe_payload['material_claims'])}`\n"
                f"- Spot Audit: {safe_payload['spot_audit'] or ''}\n"
                f"- Next Action: {safe_payload['next_action'] or ''}\n"
                f"- Structured Payload: `{_json_compact(safe_payload)}`\n"
            )

    append_ledger_entry(
        entry_type="worker_state",
        title=f"Worker {worker_id.strip()} {status}",
        statement=f"Worker `{worker_id.strip()}` recorded with status `{status}`.",
        refs=[str(run.worker_state_path), *[str(path) for path in (artifact_paths or [])]],
        status=status,
        materiality="high" if status in {"failed", "truncated", "cancelled"} else "medium",
        next_action=next_action or None,
        session_id=session_id,
        actor="runtime",
        structured_payload={
            "worker_id": safe_payload["worker_id"],
            "status": status,
            "parent_acceptance": parent_acceptance,
            "model_lane": safe_payload["model_lane"],
        },
    )
    return {
        "worker_id": safe_payload["worker_id"],
        "status": status,
        "parent_acceptance": parent_acceptance,
        "worker_state_path": str(run.worker_state_path),
        "recorded_at": timestamp,
    }


VALIDATOR_MODES = {"deterministic", "model", "manual", "skipped"}
VALIDATOR_STATUSES = {"skipped", "passed", "failed", "inconclusive"}


def record_validator_result(
    *,
    trigger: str,
    scope: str,
    mode: str,
    status: str,
    primary_result_ref: str = "",
    test_result_refs: list[str] | None = None,
    validator_findings: list[str] | None = None,
    decision_impact: str = "",
    skip_reason: str = "",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Append a selective validator result without requiring a validator engine."""

    if not trigger.strip():
        raise ValueError("validator trigger is required")
    if not scope.strip():
        raise ValueError("validator scope is required")
    if mode not in VALIDATOR_MODES:
        raise ValueError(f"Unsupported validator mode: {mode}")
    if status not in VALIDATOR_STATUSES:
        raise ValueError(f"Unsupported validator status: {status}")
    if status == "skipped" and mode != "skipped":
        raise ValueError("skipped validator status requires mode='skipped'")

    run = ensure_current_run(session_id=session_id)
    timestamp = _timestamp()
    payload = {
        "trigger": trigger.strip(),
        "scope": scope.strip(),
        "mode": mode,
        "status": status,
        "primary_result_ref": primary_result_ref.strip(),
        "test_result_refs": test_result_refs or [],
        "validator_findings": validator_findings or [],
        "decision_impact": decision_impact.strip(),
        "skip_reason": skip_reason.strip(),
        "recorded_at": timestamp,
    }

    with _STATE_LOCK:
        with run.validator_result_path.open("a", encoding="utf-8") as f:
            f.write(
                "\n### "
                f"{timestamp} - {status}\n\n"
                f"- Trigger: {payload['trigger']}\n"
                f"- Scope: {payload['scope']}\n"
                f"- Mode: `{mode}`\n"
                f"- Status: `{status}`\n"
                f"- Primary Result Ref: `{payload['primary_result_ref']}`\n"
                f"- Test Result Refs: `{_json_compact(payload['test_result_refs'])}`\n"
                f"- Validator Findings: `{_json_compact(payload['validator_findings'])}`\n"
                f"- Decision Impact: {payload['decision_impact']}\n"
                f"- Skip Reason: {payload['skip_reason']}\n"
                f"- Structured Payload: `{_json_compact(payload)}`\n"
            )

    append_ledger_entry(
        entry_type="verification" if status in {"passed", "skipped"} else "failure",
        title=f"Validator {status}",
        statement=f"Selective validator result recorded as `{status}` for `{scope}`.",
        refs=[
            str(run.validator_result_path),
            *([primary_result_ref] if primary_result_ref else []),
            *(test_result_refs or []),
        ],
        status=status,
        materiality="critical" if status in {"failed", "inconclusive"} else "high",
        next_action="Resolve validator result before accepting finalization."
        if status in {"failed", "inconclusive"} else None,
        session_id=session_id,
        actor="runtime",
        structured_payload={
            "trigger": payload["trigger"],
            "scope": payload["scope"],
            "mode": mode,
            "status": status,
        },
    )
    return {
        "validator_result_path": str(run.validator_result_path),
        "status": status,
        "recorded_at": timestamp,
    }


def _artifact_blocks(run: VestaRun) -> list[dict[str, str]]:
    try:
        text = run.artifact_manifest_path.read_text(encoding="utf-8")
    except OSError:
        return []
    blocks: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in text.splitlines():
        if line.startswith("### "):
            if current:
                blocks.append(current)
            current = {"id": line[4:].strip()}
        elif current is not None and line.startswith("- "):
            key, _, value = line[2:].partition(":")
            current[key.strip().lower().replace(" ", "_")] = value.strip().strip("`")
    if current:
        blocks.append(current)
    return blocks


def _worker_entries(run: VestaRun) -> list[dict[str, Any]]:
    try:
        text = run.worker_state_path.read_text(encoding="utf-8")
    except OSError:
        return []
    entries: list[dict[str, Any]] = []
    marker = "- Structured Payload: `"
    for line in text.splitlines():
        if not line.startswith(marker):
            continue
        raw = line[len(marker):]
        if raw.endswith("`"):
            raw = raw[:-1]
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def _latest_worker_entries(run: VestaRun) -> list[dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for entry in _worker_entries(run):
        worker_id = str(entry.get("worker_id") or "")
        if worker_id:
            latest[worker_id] = entry
    return list(latest.values())


def _expected_worker_artifacts(worker: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    contract = worker.get("output_contract")
    if isinstance(contract, dict):
        paths.extend(str(path) for path in _as_list(contract.get("expected_artifact")) if path)
        paths.extend(str(path) for path in _as_list(contract.get("expected_artifacts")) if path)
    paths.extend(str(path) for path in _as_list(worker.get("artifacts")) if path)
    seen: set[str] = set()
    unique: list[str] = []
    for path in paths:
        if path not in seen:
            unique.append(path)
            seen.add(path)
    return unique


def _artifact_path_exists(path: str, run: VestaRun) -> bool:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate.exists()
    return (Path(run.workspace_path) / candidate).exists() or (run.run_dir / candidate).exists()


def _worker_claims_need_audit(worker: dict[str, Any]) -> bool:
    claims = worker.get("material_claims") or []
    if not claims:
        return False
    return not str(worker.get("spot_audit") or "").strip()


def _worker_finalization_state(run: VestaRun) -> dict[str, Any]:
    workers = _latest_worker_entries(run)
    incomplete: list[str] = []
    failed: list[str] = []
    truncated: list[str] = []
    missing_artifacts: list[dict[str, str]] = []
    parent_acceptance_missing: list[str] = []
    claim_audit_missing: list[str] = []

    for worker in workers:
        worker_id = str(worker.get("worker_id") or "")
        status = str(worker.get("status") or "")
        if status in {"requested", "accepted", "running"}:
            incomplete.append(worker_id)
        if status in {"failed", "cancelled"}:
            failed.append(worker_id)
        if status == "truncated":
            truncated.append(worker_id)
        if status == "completed" and worker.get("parent_acceptance") != "accepted":
            parent_acceptance_missing.append(worker_id)
        if _worker_claims_need_audit(worker):
            claim_audit_missing.append(worker_id)
        for path in _expected_worker_artifacts(worker):
            if not _artifact_path_exists(path, run):
                missing_artifacts.append({"worker_id": worker_id, "path": path, "status": status})

    blockers: list[str] = []
    if incomplete:
        blockers.append("incomplete_workers")
    if failed:
        blockers.append("failed_workers")
    if truncated:
        blockers.append("truncated_workers")
    if missing_artifacts:
        blockers.append("missing_worker_artifacts")
    if parent_acceptance_missing:
        blockers.append("worker_parent_acceptance_missing")
    if claim_audit_missing:
        blockers.append("worker_claim_audit_missing")
    return {
        "workers": workers,
        "blockers": blockers,
        "incomplete": incomplete,
        "failed": failed,
        "truncated": truncated,
        "missing_artifacts": missing_artifacts,
        "parent_acceptance_missing": parent_acceptance_missing,
        "claim_audit_missing": claim_audit_missing,
    }


def _validator_entries(run: VestaRun) -> list[dict[str, Any]]:
    try:
        text = run.validator_result_path.read_text(encoding="utf-8")
    except OSError:
        return []
    entries: list[dict[str, Any]] = []
    marker = "- Structured Payload: `"
    for line in text.splitlines():
        if not line.startswith(marker):
            continue
        raw = line[len(marker):]
        if raw.endswith("`"):
            raw = raw[:-1]
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def _validator_finalization_state(run: VestaRun) -> dict[str, Any]:
    entries = _validator_entries(run)
    if not entries:
        return {"status": "absent", "entry": None, "blockers": []}
    entry = entries[-1]
    status = str(entry.get("status") or "absent")
    blockers: list[str] = []
    if status == "failed":
        blockers.append("validator_failed")
    elif status == "inconclusive":
        blockers.append("validator_inconclusive")
    elif status == "skipped" and not str(entry.get("skip_reason") or "").strip():
        blockers.append("validator_skip_reason_missing")
    return {"status": status, "entry": entry, "blockers": blockers}


def write_control_plane_snapshot(
    *,
    session_id: str | None = None,
    next_action: str | None = None,
) -> dict[str, Any]:
    """Write a compact local control-plane snapshot from Vesta artifact files."""

    run = ensure_current_run(session_id=session_id)
    timestamp = _timestamp()
    sid = session_id or os.getenv("HERMES_SESSION_ID") or ""
    finalization_status = _finalization_status(run)
    validator_state = _validator_finalization_state(run)
    worker_state = _worker_finalization_state(run)
    resolved_next_action = (next_action or "").strip() or _latest_ledger_next_action(run) or "Consult ledger."

    content = f"""# Vesta Control Plane Snapshot

Run ID: `{run.run_id}`
Generated At: `{timestamp}`
Source Of Truth: Vesta artifact files in `{run.run_dir}`

## Minimum Visible Fields

- Run ID: `{run.run_id}`
- Run Path: `{run.run_dir}`
- Active Hermes Session ID: `{sid}`
- Ledger Path: `{run.ledger_path}`
- Worker State Path: `{run.worker_state_path}`
- Finalization Path: `{run.finalization_path}`
- Validator Result Path: `{run.validator_result_path}`

## Status

- Finalization Status: `{finalization_status}`
- Validator Status: `{validator_state.get('status', 'absent')}`
- Latest Next Action: {resolved_next_action}

## Worker Summary

{_render_worker_summary(worker_state)}

## Finalization Excerpt

```markdown
{_read_tail(run.finalization_path, 2000)}
```

## Visibility Contract

- This file is a downstream snapshot, not authoritative runtime state.
- TUI, ACP, and dashboard surfaces should read Vesta artifacts instead of
  inferring truth from live events.
"""
    with _STATE_LOCK:
        run.control_plane_path.write_text(content, encoding="utf-8")

    append_ledger_entry(
        entry_type="checkpoint",
        title="Control-plane snapshot written",
        statement="Control-plane visibility snapshot was generated from Vesta artifacts.",
        refs=[str(run.control_plane_path), str(run.ledger_path), str(run.finalization_path)],
        status="active",
        materiality="medium",
        next_action=resolved_next_action,
        session_id=session_id,
        actor="runtime",
        structured_payload={
            "finalization_status": finalization_status,
            "validator_status": validator_state.get("status", "absent"),
        },
    )
    return {
        "run_id": run.run_id,
        "control_plane_path": str(run.control_plane_path),
        "finalization_status": finalization_status,
        "validator_status": validator_state.get("status", "absent"),
        "next_action": resolved_next_action,
    }


def write_handoff(
    *,
    objective: str = "",
    completed_work: list[str] | None = None,
    next_action: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Write a fresh-context handoff from Vesta files, not transcript memory."""

    run = ensure_current_run(session_id=session_id)
    timestamp = _timestamp()
    ledger_entries = _ledger_entry_summaries(run)
    finalization_status = _finalization_status(run)
    validator_state = _validator_finalization_state(run)
    worker_state = _worker_finalization_state(run)
    resolved_next_action = (next_action or "").strip() or _latest_ledger_next_action(run) or "Continue from handoff."
    resolved_objective = (objective or "").strip() or "See run objective and ledger entries."

    content = f"""# Vesta Handoff

Run ID: `{run.run_id}`
Generated At: `{timestamp}`
Source: Vesta run files, not transcript memory.

## Current Objective

{resolved_objective}

## Product Runtime Decisions

{_render_ledger_group(ledger_entries, {"decision"}, "- none recorded")}

## Completed Work

{_render_list(completed_work or [], empty="- see verification/finalization state below")}

## Verified Claims

{_render_ledger_group(ledger_entries, {"claim", "verification"}, "- none recorded")}

## Open Gaps

{_render_ledger_group(ledger_entries, {"gap", "contradiction", "failure"}, "- none recorded")}

## Artifacts

- Run: `{run.run_md_path}`
- Ledger: `{run.ledger_path}`
- Raw index: `{run.raw_index_path}`
- Artifact manifest: `{run.artifact_manifest_path}`
- Worker state: `{run.worker_state_path}`
- Validator result: `{run.validator_result_path}`
- Finalization: `{run.finalization_path}`
- Control-plane snapshot: `{run.control_plane_path}`
- Handoff: `{run.handoff_path}`

Artifact manifest excerpt:

```markdown
{_read_tail(run.artifact_manifest_path, 2000)}
```

## Raw Refs

{_render_raw_ref_summary(run)}

## Worker State

{_render_worker_summary(worker_state)}

## Verification And Finalization

- Finalization Status: `{finalization_status}`
- Validator Status: `{validator_state.get('status', 'absent')}`

Finalization excerpt:

```markdown
{_handoff_safe_excerpt(run.finalization_path, 3000)}
```

## Residual Risk

{_render_residual_risk(finalization_status, validator_state, worker_state)}

## Next Action

{resolved_next_action}

## Paths To Run State

- Run Directory: `{run.run_dir}`
- Ledger Path: `{run.ledger_path}`
- Resume Packet: `{run.resume_packet_path}`
- Control Plane Snapshot: `{run.control_plane_path}`
"""
    with _STATE_LOCK:
        run.handoff_path.write_text(content, encoding="utf-8")

    append_ledger_entry(
        entry_type="checkpoint",
        title="Handoff generated",
        statement="Fresh-context handoff generated from Vesta run files.",
        refs=[str(run.handoff_path), str(run.ledger_path), str(run.finalization_path)],
        status="active",
        materiality="critical",
        next_action=resolved_next_action,
        session_id=session_id,
        actor="runtime",
        structured_payload={
            "finalization_status": finalization_status,
            "validator_status": validator_state.get("status", "absent"),
        },
    )
    return {
        "run_id": run.run_id,
        "handoff_path": str(run.handoff_path),
        "finalization_status": finalization_status,
        "next_action": resolved_next_action,
    }


def _finalization_status(run: VestaRun) -> str:
    try:
        text = run.finalization_path.read_text(encoding="utf-8")
    except OSError:
        return "not_written"
    for line in text.splitlines():
        if line.startswith("Verdict: `") and line.endswith("`"):
            return line[len("Verdict: `"):-1]
    return "not_written"


def _latest_ledger_next_action(run: VestaRun) -> str:
    try:
        lines = run.ledger_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        if line.startswith("- Next Action: "):
            return line[len("- Next Action: "):].strip()
    return ""


def _read_tail(path: Path, chars: int) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return "- not written"
    return text[-chars:]


def _handoff_safe_excerpt(path: Path, chars: int) -> str:
    excerpt = _read_tail(path, chars)
    return excerpt.replace("## Next Action", "### Finalization Next Action")


def _ledger_entry_summaries(run: VestaRun) -> list[dict[str, str]]:
    try:
        lines = run.ledger_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in lines:
        if line.startswith("### "):
            if current:
                entries.append(current)
            current = {"title": line[4:].strip()}
            continue
        if current is None or not line.startswith("- "):
            continue
        key, _, value = line[2:].partition(":")
        norm_key = key.strip().lower().replace(" ", "_")
        current[norm_key] = value.strip().strip("`")
    if current:
        entries.append(current)
    return entries


def _render_ledger_group(entries: list[dict[str, str]], types: set[str], empty: str) -> str:
    lines = []
    for entry in entries:
        if entry.get("type") not in types:
            continue
        statement = entry.get("statement", "")
        status = entry.get("status", "")
        refs = entry.get("refs", "")
        suffix = f" Status: `{status}`." if status else ""
        refs_text = f" Refs: {refs}." if refs else ""
        lines.append(f"- {statement}{suffix}{refs_text}")
    return "\n".join(lines) if lines else empty


def _render_raw_ref_summary(run: VestaRun) -> str:
    try:
        lines = run.raw_index_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return "- none recorded"
    refs = [line[4:].strip() for line in lines if line.startswith("### ")]
    if not refs:
        return "- none recorded"
    return "\n".join(f"- `{ref}`" for ref in refs[-20:])


def _render_residual_risk(
    finalization_status: str,
    validator_state: dict[str, Any],
    worker_state: dict[str, Any],
) -> str:
    risks: list[str] = []
    if finalization_status not in {"accepted", "accepted_with_gaps"}:
        risks.append(f"Finalization status is `{finalization_status}`.")
    if validator_state.get("blockers"):
        risks.extend(f"Validator blocker: `{blocker}`." for blocker in validator_state["blockers"])
    if worker_state.get("blockers"):
        risks.extend(f"Worker blocker: `{blocker}`." for blocker in worker_state["blockers"])
    if validator_state.get("status") == "absent":
        risks.append("Validator was absent; this is not a validator pass.")
    return "\n".join(f"- {risk}" for risk in risks) if risks else "- none recorded"


def write_finalization(
    *,
    objective: str,
    verification: str = "",
    skip_reason: str = "",
    unsupported_claims: list[str] | None = None,
    failures: list[str] | None = None,
    contradictions: list[str] | None = None,
    gaps: list[str] | None = None,
    next_action: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Write finalization packet from recorded run state."""

    run = ensure_current_run(session_id=session_id)
    artifacts = _artifact_blocks(run)
    worker_state = _worker_finalization_state(run)
    validator_state = _validator_finalization_state(run)
    missing_artifacts = [
        artifact for artifact in artifacts
        if artifact.get("status") in {"expected", "missing"}
    ]
    unsupported_claims = unsupported_claims or []
    failures = failures or []
    contradictions = contradictions or []
    gaps = gaps or []
    blockers = []
    if missing_artifacts:
        blockers.append("missing_artifacts")
    if unsupported_claims:
        blockers.append("unsupported_claims")
    if failures:
        blockers.append("failures")
    if contradictions:
        blockers.append("contradictions")
    if not verification and not skip_reason:
        blockers.append("verification_or_skip_reason_missing")
    blockers.extend(worker_state["blockers"])
    blockers.extend(validator_state["blockers"])
    verdict = "blocked" if blockers else ("accepted_with_gaps" if gaps else "accepted")
    resolved_next = (next_action or "").strip()
    if verdict == "blocked" and not resolved_next:
        resolved_next = "Resolve finalization blockers."

    timestamp = _timestamp()
    content = f"""# Vesta Finalization

Run ID: `{run.run_id}`
Generated At: `{timestamp}`
Verdict: `{verdict}`

## Objective

{objective}

## Outputs

- Artifact manifest: `{run.artifact_manifest_path}`
- Worker state: `{run.worker_state_path}`
- Validator result: `{run.validator_result_path}`

## Verification

{verification or f"Skipped: {skip_reason}"}

## Material Claims

{_render_list(unsupported_claims, empty="- none recorded")}

## Gaps And Contradictions

Gaps:
{_render_list(gaps, empty="- none recorded")}

Contradictions:
{_render_list(contradictions, empty="- none recorded")}

## Failures

{_render_list(failures, empty="- none recorded")}

## Workers

{_render_worker_summary(worker_state)}

## Validator

{_render_validator_summary(validator_state)}

## Missing Artifacts

{_render_artifact_list(missing_artifacts)}

## Missing Worker Artifacts

{_render_worker_artifact_list(worker_state["missing_artifacts"])}

## Residual Risk

{_render_list(blockers, empty="- none recorded")}

## Next Action

{resolved_next or "- none"}
"""
    run.finalization_path.write_text(content, encoding="utf-8")
    append_ledger_entry(
        entry_type="checkpoint",
        title="Run finalization",
        statement=f"Finalization verdict is `{verdict}`.",
        refs=[str(run.finalization_path), str(run.artifact_manifest_path)],
        status=verdict,
        materiality="critical",
        next_action=resolved_next or None,
        session_id=session_id,
        actor="runtime",
        structured_payload={"verdict": verdict, "blockers": blockers},
    )
    return {
        "run_id": run.run_id,
        "finalization_path": str(run.finalization_path),
        "verdict": verdict,
        "blockers": blockers,
        "next_action": resolved_next,
    }


def _render_list(items: list[str], *, empty: str) -> str:
    if not items:
        return empty
    return "\n".join(f"- {item}" for item in items)


def _render_artifact_list(artifacts: list[dict[str, str]]) -> str:
    if not artifacts:
        return "- none recorded"
    return "\n".join(
        f"- `{artifact.get('path', '')}` status `{artifact.get('status', '')}`"
        for artifact in artifacts
    )


def _render_worker_artifact_list(artifacts: list[dict[str, str]]) -> str:
    if not artifacts:
        return "- none recorded"
    return "\n".join(
        f"- Worker `{artifact.get('worker_id', '')}` expected `{artifact.get('path', '')}`"
        f" while status is `{artifact.get('status', '')}`"
        for artifact in artifacts
    )


def _render_worker_summary(worker_state: dict[str, Any]) -> str:
    workers = worker_state.get("workers") or []
    if not workers:
        return "- none recorded"
    lines = []
    for worker in workers:
        lines.append(
            f"- `{worker.get('worker_id', '')}` status `{worker.get('status', '')}`, "
            f"parent acceptance `{worker.get('parent_acceptance', '')}`, "
            f"model lane `{worker.get('model_lane', '')}`"
        )
    if worker_state.get("blockers"):
        lines.append("")
        lines.append("Blockers:")
        lines.extend(f"- {blocker}" for blocker in worker_state["blockers"])
    return "\n".join(lines)


def _render_validator_summary(validator_state: dict[str, Any]) -> str:
    status = validator_state.get("status", "absent")
    entry = validator_state.get("entry")
    if not entry:
        return f"- Validator Status: `{status}`"
    lines = [
        f"- Validator Status: `{status}`",
        f"- Mode: `{entry.get('mode', '')}`",
        f"- Trigger: {entry.get('trigger', '')}",
        f"- Scope: {entry.get('scope', '')}",
        f"- Primary Result Ref: `{entry.get('primary_result_ref', '')}`",
        f"- Test Result Refs: `{_json_compact(entry.get('test_result_refs') or [])}`",
        f"- Findings: `{_json_compact(entry.get('validator_findings') or [])}`",
        f"- Decision Impact: {entry.get('decision_impact', '')}",
    ]
    if entry.get("skip_reason"):
        lines.append(f"- Skip Reason: {entry.get('skip_reason', '')}")
    if validator_state.get("blockers"):
        lines.append("")
        lines.append("Blockers:")
        lines.extend(f"- {blocker}" for blocker in validator_state["blockers"])
    return "\n".join(lines)
