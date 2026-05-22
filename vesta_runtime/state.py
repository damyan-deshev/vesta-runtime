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
    context_length: int | None = None


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


def _parse_md_field(path: Path, field: str) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    prefix = f"{field}: `"
    for line in text.splitlines():
        if line.startswith(prefix) and line.endswith("`"):
            return line[len(prefix):-1]
    return ""


def _run_status_from_dir(run_dir: Path) -> str:
    finalization = run_dir / "finalization.md"
    if not finalization.exists():
        return "not_written"
    return _parse_md_field(finalization, "Verdict") or "not_written"


def _infer_run_lineage(
    *,
    workspace_hash: str,
    current_run_id: str,
    parent_session_id: str | None,
) -> dict[str, str]:
    """Infer lightweight recovery lineage from prior runs in the same workspace."""

    lineage = {
        "resumes_run_id": "",
        "recovery_of_run_id": "",
        "supersedes_run_id": "",
        "resumed_from_session_id": parent_session_id or "",
    }
    runs_root = get_hermes_home() / "vesta" / "workspaces" / workspace_hash / "runs"
    try:
        candidates = [
            path for path in runs_root.iterdir()
            if path.is_dir() and path.name != current_run_id
        ]
    except OSError:
        return lineage
    candidates.sort(key=lambda path: (path.stat().st_mtime if path.exists() else 0, path.name))
    for prior in reversed(candidates):
        if _run_status_from_dir(prior) not in {"blocked", "failed"}:
            continue
        lineage["resumes_run_id"] = prior.name
        lineage["recovery_of_run_id"] = prior.name
        lineage["supersedes_run_id"] = prior.name
        if not lineage["resumed_from_session_id"]:
            lineage["resumed_from_session_id"] = _parse_md_field(prior / "run.md", "Hermes Session ID")
        break
    return lineage


def _set_env_for_run(run: VestaRun) -> None:
    os.environ["VESTA_RUN_ID"] = run.run_id
    os.environ["VESTA_RUN_DIR"] = str(run.run_dir)
    os.environ["VESTA_LEDGER_PATH"] = str(run.ledger_path)
    if run.context_length and run.context_length > 0:
        os.environ["VESTA_CONTEXT_LENGTH_TOKENS"] = str(run.context_length)
    else:
        os.environ.pop("VESTA_CONTEXT_LENGTH_TOKENS", None)


def set_current_run(run: VestaRun | None) -> None:
    """Set the current run for this execution context."""

    _CURRENT_RUN.set(run)
    if run is not None:
        _set_env_for_run(run)
    else:
        for key in (
            "VESTA_RUN_ID",
            "VESTA_RUN_DIR",
            "VESTA_LEDGER_PATH",
            "VESTA_CONTEXT_LENGTH_TOKENS",
        ):
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
    try:
        context_length = int(os.getenv("VESTA_CONTEXT_LENGTH_TOKENS") or "0") or None
    except (TypeError, ValueError):
        context_length = None
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
        context_length=context_length,
    )
    if run.run_dir.exists():
        set_current_run(run)
        return run
    return None


def _run_from_dir(run_dir: str | os.PathLike[str]) -> VestaRun | None:
    """Build a VestaRun handle for an existing run directory."""

    path = Path(run_dir)
    if not path.is_dir():
        return None
    run_md = path / "run.md"
    run_id = _parse_md_field(run_md, "Run ID") or path.name
    try:
        context_length = int(_parse_md_field(run_md, "Context Length Tokens") or "0") or None
    except (TypeError, ValueError):
        context_length = None
    return VestaRun(
        run_id=run_id,
        workspace_hash=_parse_md_field(run_md, "Workspace Hash"),
        workspace_path=_parse_md_field(run_md, "Workspace Path"),
        run_dir=path,
        run_md_path=run_md,
        ledger_path=path / "ledger.md",
        resume_packet_path=path / "resume-packet.md",
        artifact_manifest_path=path / "artifact-manifest.md",
        finalization_path=path / "finalization.md",
        worker_state_path=path / "worker-state.md",
        validator_result_path=path / "validator-result.md",
        control_plane_path=path / "control-plane.md",
        handoff_path=path / "handoff.md",
        raw_dir=path / "raw",
        raw_index_path=path / "raw" / "index.md",
        created_at=_parse_md_field(run_md, "Created At"),
        context_length=context_length,
    )


def _run_mentions_session(run_dir: Path, session_id: str) -> bool:
    if not session_id:
        return False
    run_md = run_dir / "run.md"
    if _parse_md_field(run_md, "Hermes Session ID") == session_id:
        return True
    if _parse_md_field(run_md, "Hermes Parent Session ID") == session_id:
        return True
    try:
        text = run_md.read_text(encoding="utf-8")
    except OSError:
        return False
    needles = (
        f"- {session_id}",
        f"Old Session ID: `{session_id}`",
        f"New Session ID: `{session_id}`",
        f"Resumed From Session ID: `{session_id}`",
    )
    return any(needle in text for needle in needles)


def find_latest_run_for_session(session_id: str) -> dict[str, Any] | None:
    """Find the newest Vesta run that references a Hermes session id."""

    sid = (session_id or "").strip()
    if not sid:
        return None
    runs_root = get_hermes_home() / "vesta" / "workspaces"
    candidates: list[Path] = []
    try:
        workspaces = [path for path in runs_root.iterdir() if path.is_dir()]
    except OSError:
        return None
    for workspace in workspaces:
        try:
            run_dirs = [path for path in (workspace / "runs").iterdir() if path.is_dir()]
        except OSError:
            continue
        candidates.extend(run_dir for run_dir in run_dirs if _run_mentions_session(run_dir, sid))
    if not candidates:
        return None
    candidates.sort(key=lambda p: (p.stat().st_mtime if p.exists() else 0, p.name))
    run = _run_from_dir(candidates[-1])
    if run is None:
        return None
    status = _run_status_for_run(run)
    status["matched_session_id"] = sid
    return status


def create_run(
    *,
    session_id: str,
    parent_session_id: str | None = None,
    task_id: str | None = None,
    workspace_path: str | os.PathLike[str] | None = None,
    model: str | None = None,
    provider: str | None = None,
    platform: str | None = None,
    context_length: int | None = None,
    run_id: str | None = None,
    resumes_run_id: str | None = None,
    recovery_of_run_id: str | None = None,
    supersedes_run_id: str | None = None,
    resumed_from_session_id: str | None = None,
) -> VestaRun:
    """Create and bind a Vesta run with eager Markdown seed files."""

    resolved_workspace = _workspace_path(workspace_path)
    workspace_hash = _workspace_hash(resolved_workspace)
    created_at = _timestamp()
    try:
        resolved_context_length = int(context_length or 0) or None
    except (TypeError, ValueError):
        resolved_context_length = None
    rid = run_id or _new_run_id()
    run_dir = get_hermes_home() / "vesta" / "workspaces" / workspace_hash / "runs" / rid
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    lineage = _infer_run_lineage(
        workspace_hash=workspace_hash,
        current_run_id=rid,
        parent_session_id=parent_session_id,
    )
    if resumes_run_id is not None:
        lineage["resumes_run_id"] = resumes_run_id
    if recovery_of_run_id is not None:
        lineage["recovery_of_run_id"] = recovery_of_run_id
    if supersedes_run_id is not None:
        lineage["supersedes_run_id"] = supersedes_run_id
    if resumed_from_session_id is not None:
        lineage["resumed_from_session_id"] = resumed_from_session_id

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
        context_length=resolved_context_length,
    )

    _write_if_missing(run.run_md_path, _render_run_seed(
        run=run,
        session_id=session_id,
        parent_session_id=parent_session_id,
        task_id=task_id,
        model=model,
        provider=provider,
        platform=platform,
        context_length=resolved_context_length,
        lineage=lineage,
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


def _active_model_config() -> dict[str, str]:
    try:
        from hermes_cli.config import load_config

        cfg = load_config().get("model", {})
        if isinstance(cfg, dict):
            return {
                "model": str(cfg.get("default") or cfg.get("model") or "").strip(),
                "provider": str(cfg.get("provider") or "").strip(),
                "base_url": str(cfg.get("base_url") or "").strip(),
            }
    except Exception:
        pass
    return {"model": "", "provider": "", "base_url": ""}


def _active_delegation_config() -> dict[str, str]:
    try:
        from hermes_cli.config import load_config

        cfg = load_config().get("delegation", {})
        if isinstance(cfg, dict):
            return {
                "model": str(cfg.get("model") or "").strip(),
                "provider": str(cfg.get("provider") or "").strip(),
                "base_url": str(cfg.get("base_url") or "").strip(),
            }
    except Exception:
        pass
    return {"model": "", "provider": "", "base_url": ""}


def _render_run_seed(
    *,
    run: VestaRun,
    session_id: str,
    parent_session_id: str | None,
    task_id: str | None,
    model: str | None,
    provider: str | None,
    platform: str | None,
    context_length: int | None,
    lineage: dict[str, str] | None = None,
) -> str:
    parent = parent_session_id or ""
    session_lineage = f"- {session_id}"
    if parent:
        session_lineage = f"- {parent}\n- {session_id}"
    run_link = lineage or {}
    model_cfg = _active_model_config()
    delegation_cfg = _active_delegation_config()
    resolved_model = model or model_cfg.get("model", "")
    resolved_provider = provider or model_cfg.get("provider", "")
    return f"""# Vesta Run

Run ID: `{run.run_id}`
Created At: `{run.created_at}`
Workspace Hash: `{run.workspace_hash}`
Workspace Path: `{run.workspace_path}`
Hermes Session ID: `{session_id}`
Hermes Parent Session ID: `{parent}`
Task ID: `{task_id or ''}`
Model: `{resolved_model or ''}`
Provider: `{resolved_provider or ''}`
Base URL: `{model_cfg.get('base_url', '')}`
Platform: `{platform or ''}`
Context Length Tokens: `{context_length or ''}`
Delegation Model: `{delegation_cfg.get('model', '')}`
Delegation Provider: `{delegation_cfg.get('provider', '')}`
Delegation Base URL: `{delegation_cfg.get('base_url', '')}`

## Hermes Session Lineage

{session_lineage}

## Run Recovery Lineage

- Resumes Run ID: `{run_link.get('resumes_run_id', '')}`
- Recovery Of Run ID: `{run_link.get('recovery_of_run_id', '')}`
- Supersedes Run ID: `{run_link.get('supersedes_run_id', '')}`
- Resumed From Session ID: `{run_link.get('resumed_from_session_id', '')}`

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
    eval_cfg = cfg.get("eval", {})
    return f"""## Vesta Effective Config

- Retrieval Mode: `{retrieval.get('mode', 'disciplined')}`
- Broad Read Line Threshold: `{retrieval.get('broad_read_line_threshold', 200)}`
- Broad Read Byte Threshold: `{retrieval.get('broad_read_byte_threshold', 20_000)}`
- Broad Read Token Threshold: `{retrieval.get('broad_read_token_threshold', 12_000)}`
- Whole Document Token Threshold: `{whole_document.get('token_threshold', 100_000)}`
- Whole Document Max Chunk Tokens: `{whole_document.get('max_chunk_tokens', 20_000)}`
- Raw Retention Retain By Default: `{raw_retention.get('retain_by_default', True)}`
- Raw Retention Purge Preserves Manifest: `{raw_retention.get('purge_preserves_manifest', True)}`
- Eval Enabled: `{eval_cfg.get('enabled', False)}`
- Eval Allow Background Review: `{eval_cfg.get('allow_background_review', False)}`
- Eval Contract Profile: `{eval_cfg.get('contract_profile', 'artifact_positive')}`

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


def _refresh_validator_status_header(run: VestaRun, status: str, timestamp: str) -> None:
    try:
        text = run.validator_result_path.read_text(encoding="utf-8")
    except OSError:
        return
    if "- Validator Status: `" in text:
        text = re.sub(
            r"- Validator Status: `[^`]*`",
            f"- Validator Status: `{status}`",
            text,
            count=1,
        )
    else:
        text = text.replace("## Status\n", f"## Status\n\n- Validator Status: `{status}`\n", 1)
    if "- Last Validator Update: `" in text:
        text = re.sub(
            r"- Last Validator Update: `[^`]*`",
            f"- Last Validator Update: `{timestamp}`",
            text,
            count=1,
        )
    else:
        text = text.replace(
            f"- Validator Status: `{status}`",
            f"- Validator Status: `{status}`\n- Last Validator Update: `{timestamp}`",
            1,
        )
    run.validator_result_path.write_text(text, encoding="utf-8")


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
_NON_LOCAL_ARTIFACT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
RESEARCH_ARTIFACT_SECTIONS = {
    "sources": "Sources",
    "paper_coverage": "Paper Coverage",
    "claims_verdict": "Claims / Verdict",
    "gaps": "Gaps",
}


def _is_local_artifact_path(path: str) -> bool:
    value = path.strip()
    return bool(value) and _NON_LOCAL_ARTIFACT_RE.match(value) is None


def _resolve_artifact_path(path: str, run: VestaRun) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve(strict=False)
    base = Path(run.workspace_path) if run.workspace_path else Path.cwd()
    return (base / candidate).resolve(strict=False)


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _artifact_verification(path: str, requested_status: str, run: VestaRun) -> dict[str, Any]:
    info: dict[str, Any] = {
        "requested_status": requested_status,
        "status": requested_status,
        "verified": False,
        "canonical_path": path.strip(),
        "verification_note": "",
    }
    if not _is_local_artifact_path(path):
        if requested_status == "exists":
            info["verification_note"] = "Non-local artifact path was not filesystem-verified."
        return info

    resolved = _resolve_artifact_path(path, run)
    info["canonical_path"] = str(resolved)
    if requested_status != "exists":
        return info

    if not resolved.exists():
        info["status"] = "missing"
        info["verification_note"] = "Requested status `exists`, but the filesystem path is missing."
        return info

    info["verified"] = True
    info["verified_at"] = _timestamp()
    info["size_bytes"] = resolved.stat().st_size if resolved.is_file() else None
    if resolved.is_file():
        info["content_hash"] = _hash_file(resolved)
    return info


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

    requested_status = status
    if requested_status not in ARTIFACT_STATUSES:
        raise ValueError(f"Unsupported artifact status: {requested_status}")
    run = ensure_current_run(session_id=session_id)
    artifact_id = f"art_{uuid.uuid4().hex[:10]}"
    timestamp = _timestamp()
    verification = _artifact_verification(path, requested_status, run)
    status = str(verification["status"])
    with _STATE_LOCK:
        with run.artifact_manifest_path.open("a", encoding="utf-8") as f:
            f.write(
                "\n### "
                f"{artifact_id}\n\n"
                f"- Path: `{path}`\n"
                f"- Canonical Path: `{verification.get('canonical_path', path)}`\n"
                f"- Type: `{artifact_type}`\n"
                f"- Expected By: `{expected_by}`\n"
                f"- Requested Status: `{requested_status}`\n"
                f"- Status: `{status}`\n"
                f"- Impact If Missing: {impact_if_missing}\n"
                f"- Recorded At: `{timestamp}`\n"
            )
            if verification.get("verified"):
                f.write(f"- Verified At: `{verification.get('verified_at', '')}`\n")
                if verification.get("content_hash"):
                    f.write(f"- Content Hash: `{verification['content_hash']}`\n")
                if verification.get("size_bytes") is not None:
                    f.write(f"- Size Bytes: `{verification['size_bytes']}`\n")
            if verification.get("verification_note"):
                f.write(f"- Verification Note: {verification['verification_note']}\n")
    append_ledger_entry(
        entry_type="artifact",
        title=f"Artifact {status}: {path}",
        statement=(
            f"Artifact `{path}` recorded with status `{status}`."
            if status == requested_status
            else f"Artifact `{path}` requested as `{requested_status}` but verified as `{status}`."
        ),
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
            "requested_status": requested_status,
            "canonical_path": verification.get("canonical_path"),
            "verified": verification.get("verified", False),
            "content_hash": verification.get("content_hash"),
            "verification_note": verification.get("verification_note", ""),
        },
    )
    return {
        "artifact_id": artifact_id,
        "artifact_manifest_path": str(run.artifact_manifest_path),
        "status": status,
        "requested_status": requested_status,
        "canonical_path": verification.get("canonical_path"),
        "verified": verification.get("verified", False),
        "content_hash": verification.get("content_hash"),
        "verification_note": verification.get("verification_note", ""),
    }


def _research_artifact_section_limit() -> int:
    retrieval = _active_vesta_config().get("retrieval", {})
    try:
        value = int(retrieval.get("broad_read_byte_threshold", 20_000))
    except (TypeError, ValueError):
        value = 20_000
    return value if value > 0 else 20_000


def _normalize_research_artifact_section(section: str) -> tuple[str, str]:
    key = re.sub(r"[^a-z0-9]+", "_", (section or "").strip().lower()).strip("_")
    aliases = {
        "paper": "paper_coverage",
        "papers": "paper_coverage",
        "coverage": "paper_coverage",
        "claims": "claims_verdict",
        "verdict": "claims_verdict",
        "claims_and_verdict": "claims_verdict",
        "claims_verdict": "claims_verdict",
        "claim_verdict": "claims_verdict",
        "source": "sources",
        "gap": "gaps",
    }
    key = aliases.get(key, key)
    if key not in RESEARCH_ARTIFACT_SECTIONS:
        allowed = ", ".join(sorted(RESEARCH_ARTIFACT_SECTIONS))
        raise ValueError(f"Unsupported research artifact section `{section}`. Use one of: {allowed}.")
    return key, RESEARCH_ARTIFACT_SECTIONS[key]


def write_research_artifact_section(
    *,
    path: str,
    section: str,
    content: str,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Append one bounded section to a Vesta research artifact."""

    run = ensure_current_run(session_id=session_id)
    if not path.strip():
        raise ValueError("Research artifact path is required")
    if not isinstance(content, str):
        raise TypeError("Research artifact section content must be a string")
    section_key, section_title = _normalize_research_artifact_section(section)
    max_chars = _research_artifact_section_limit()
    content_chars = len(content)
    if content_chars > max_chars:
        raise ValueError(
            "Research artifact section is too large: "
            f"{content_chars} chars exceeds limit {max_chars}. "
            "Split the section or write a compact evidence index."
        )

    artifact_path = _resolve_artifact_path(path, run)
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = _timestamp()
    header = (
        "# Vesta Research Artifact\n\n"
        f"Run ID: `{run.run_id}`\n"
        f"Created At: `{timestamp}`\n"
        f"Path: `{path}`\n"
    )
    section_block = (
        f"\n\n## {section_title}\n\n"
        f"- Section Key: `{section_key}`\n"
        f"- Appended At: `{timestamp}`\n"
        f"- Content Chars: `{content_chars}`\n\n"
        f"{content.strip()}\n"
    )

    with _STATE_LOCK:
        if not artifact_path.exists():
            artifact_path.write_text(header, encoding="utf-8")
        with artifact_path.open("a", encoding="utf-8") as f:
            f.write(section_block)

    artifact = record_artifact(
        path=path,
        artifact_type="research_artifact",
        expected_by="research_artifact_section_write",
        status="exists",
        impact_if_missing="Research artifact section writer produced this report.",
        session_id=session_id,
    )
    append_ledger_entry(
        entry_type="artifact",
        title=f"Research artifact section appended: {section_title}",
        statement=f"Section `{section_key}` appended to research artifact `{path}`.",
        refs=[path, str(artifact_path), str(run.artifact_manifest_path)],
        status="exists",
        materiality="medium",
        session_id=session_id,
        actor="runtime",
        structured_payload={
            "section": section_key,
            "path": path,
            "canonical_path": str(artifact_path),
            "content_chars": content_chars,
            "max_chars": max_chars,
        },
    )
    return {
        "run_id": run.run_id,
        "path": path,
        "canonical_path": str(artifact_path),
        "section": section_key,
        "section_title": section_title,
        "content_chars": content_chars,
        "max_chars": max_chars,
        "artifact_manifest_path": str(run.artifact_manifest_path),
        "artifact_status": artifact.get("status"),
        "artifact_verified": artifact.get("verified", False),
    }


WORKER_STATUSES = {
    "requested",
    "accepted",
    "rejected",
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


def _payload_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(_payload_present(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_payload_present(item) for item in value)
    return True


def _latest_worker_entry_for_id(run: VestaRun, worker_id: str) -> dict[str, Any]:
    latest: dict[str, Any] = {}
    try:
        entries = _worker_entries(run)
    except Exception:
        return latest
    for entry in entries:
        if str(entry.get("worker_id") or "") == worker_id:
            latest = entry
    return latest


def _carry_worker_field(
    explicit_value: Any,
    previous: dict[str, Any],
    field: str,
    default: Any,
) -> Any:
    if _payload_present(explicit_value):
        return explicit_value
    previous_value = previous.get(field)
    if _payload_present(previous_value):
        return previous_value
    return default


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
    child_run_id: str = "",
    expected_artifact_paths: list[str] | None = None,
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
    resolved_worker_id = worker_id.strip()
    previous_worker = _latest_worker_entry_for_id(run, resolved_worker_id)
    resolved_output_contract = _carry_worker_field(
        output_contract,
        previous_worker,
        "output_contract",
        {},
    )
    resolved_child_session_id = _carry_worker_field(
        child_session_id,
        previous_worker,
        "child_session_id",
        "",
    )
    resolved_child_run_id = _carry_worker_field(
        child_run_id,
        previous_worker,
        "child_run_id",
        "",
    )
    resolved_expected_artifact_paths = _carry_worker_field(
        expected_artifact_paths,
        previous_worker,
        "expected_artifact_paths",
        [],
    )
    resolved_artifact_paths = _carry_worker_field(
        artifact_paths,
        previous_worker,
        "artifacts",
        [],
    )
    resolved_material_claims = _carry_worker_field(
        material_claims,
        previous_worker,
        "material_claims",
        [],
    )
    safe_payload = _sanitize_runtime_payload({
        "worker_id": resolved_worker_id,
        "parent_run_id": run.run_id,
        "child_session_id": str(resolved_child_session_id).strip(),
        "child_run_id": str(resolved_child_run_id).strip(),
        "objective": objective.strip(),
        "output_contract": resolved_output_contract,
        "model_lane": model_lane.strip(),
        "status": status,
        "expected_artifact_paths": _as_list(resolved_expected_artifact_paths),
        "artifacts": _as_list(resolved_artifact_paths),
        "failures": failures or [],
        "gaps": gaps or [],
        "material_claims": _as_list(resolved_material_claims),
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
                f"- Child Run ID: `{safe_payload['child_run_id']}`\n"
                f"- Objective: {safe_payload['objective']}\n"
                f"- Status: `{status}`\n"
                f"- Model Lane: `{safe_payload['model_lane']}`\n"
                f"- Parent Acceptance: `{parent_acceptance}`\n"
                f"- Expected Artifact Paths: `{_json_compact(safe_payload['expected_artifact_paths'])}`\n"
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
        title=f"Worker {resolved_worker_id} {status}",
        statement=f"Worker `{resolved_worker_id}` recorded with status `{status}`.",
        refs=[str(run.worker_state_path), *[str(path) for path in safe_payload["artifacts"]]],
        status=status,
        materiality="high" if status in {"failed", "truncated", "cancelled", "rejected"} else "medium",
        next_action=next_action or None,
        session_id=session_id,
        actor="runtime",
        structured_payload={
            "worker_id": safe_payload["worker_id"],
            "status": status,
            "parent_acceptance": parent_acceptance,
            "model_lane": safe_payload["model_lane"],
            "child_session_id": safe_payload["child_session_id"],
            "child_run_id": safe_payload["child_run_id"],
        },
    )
    return {
        "worker_id": safe_payload["worker_id"],
        "status": status,
        "parent_acceptance": parent_acceptance,
        "child_session_id": safe_payload["child_session_id"],
        "child_run_id": safe_payload["child_run_id"],
        "expected_artifact_paths": safe_payload["expected_artifact_paths"],
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
        _refresh_validator_status_header(run, status, timestamp)

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


def _artifact_key(artifact: dict[str, str], run: VestaRun) -> str:
    canonical = artifact.get("canonical_path", "").strip()
    if canonical:
        return canonical
    path = artifact.get("path", "").strip()
    if not path:
        return artifact.get("id", "")
    if not _is_local_artifact_path(path):
        return path
    return str(_resolve_artifact_path(path, run))


def _latest_artifact_blocks(run: VestaRun) -> list[dict[str, str]]:
    latest: dict[str, dict[str, str]] = {}
    order: list[str] = []
    for artifact in _artifact_blocks(run):
        key = _artifact_key(artifact, run)
        if not key:
            key = artifact.get("id", "")
        if key not in latest:
            order.append(key)
        latest[key] = artifact
    return [latest[key] for key in order if key in latest]


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
    paths.extend(str(path) for path in _as_list(worker.get("expected_artifact_paths")) if path)
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
        if status in {"failed", "cancelled", "rejected"}:
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


def _run_lineage_metadata(run: VestaRun) -> dict[str, str]:
    return {
        "hermes_session_id": _parse_md_field(run.run_md_path, "Hermes Session ID"),
        "hermes_parent_session_id": _parse_md_field(run.run_md_path, "Hermes Parent Session ID"),
        "resumes_run_id": _parse_md_field(run.run_md_path, "- Resumes Run ID"),
        "recovery_of_run_id": _parse_md_field(run.run_md_path, "- Recovery Of Run ID"),
        "supersedes_run_id": _parse_md_field(run.run_md_path, "- Supersedes Run ID"),
        "resumed_from_session_id": _parse_md_field(run.run_md_path, "- Resumed From Session ID"),
    }


def _render_run_lineage_summary(run: VestaRun) -> str:
    lineage = _run_lineage_metadata(run)
    return (
        f"- Primary Hermes Session ID: `{lineage.get('hermes_session_id', '')}`\n"
        f"- Parent Hermes Session ID: `{lineage.get('hermes_parent_session_id', '')}`\n"
        f"- Resumes Run ID: `{lineage.get('resumes_run_id', '')}`\n"
        f"- Recovery Of Run ID: `{lineage.get('recovery_of_run_id', '')}`\n"
        f"- Supersedes Run ID: `{lineage.get('supersedes_run_id', '')}`\n"
        f"- Resumed From Session ID: `{lineage.get('resumed_from_session_id', '')}`"
    )


def write_control_plane_snapshot(
    *,
    session_id: str | None = None,
    next_action: str | None = None,
) -> dict[str, Any]:
    """Write a compact local control-plane snapshot from Vesta artifact files."""

    run = ensure_current_run(session_id=session_id)
    timestamp = _timestamp()
    sid = session_id or os.getenv("HERMES_SESSION_ID") or ""
    lineage = _run_lineage_metadata(run)
    primary_sid = lineage.get("hermes_session_id") or sid
    finalization_status = _finalization_status(run)
    validator_state = _validator_finalization_state(run)
    worker_state = _worker_finalization_state(run)
    artifacts = _latest_artifact_blocks(run)
    resolved_next_action = (next_action or "").strip() or _run_next_action(run) or "Consult ledger."

    content = f"""# Vesta Control Plane Snapshot

Run ID: `{run.run_id}`
Generated At: `{timestamp}`
Source Of Truth: Vesta artifact files in `{run.run_dir}`

## Minimum Visible Fields

- Run ID: `{run.run_id}`
- Run Path: `{run.run_dir}`
- Active Hermes Session ID: `{primary_sid}`
- Snapshot Requested Session ID: `{sid}`
- Ledger Path: `{run.ledger_path}`
- Worker State Path: `{run.worker_state_path}`
- Finalization Path: `{run.finalization_path}`
- Validator Result Path: `{run.validator_result_path}`

## Status

- Finalization Status: `{finalization_status}`
- Validator Status: `{validator_state.get('status', 'absent')}`
- Latest Next Action: {resolved_next_action}

## Run Lineage

{_render_run_lineage_summary(run)}

## Worker Summary

{_render_worker_summary(worker_state)}

## Artifact Summary

{_render_artifact_list(artifacts)}

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
        "lineage": lineage,
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
    resolved_next_action = (next_action or "").strip() or _run_next_action(run) or "Continue from handoff."
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


def _finalization_next_action(run: VestaRun) -> str:
    try:
        lines = run.finalization_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    in_section = False
    collected: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == "## Next Action":
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if in_section and stripped:
            collected.append(stripped[2:].strip() if stripped.startswith("- ") else stripped)
    return " ".join(collected).strip()


def _run_next_action(run: VestaRun) -> str:
    if _finalization_status(run) != "not_written":
        return _finalization_next_action(run) or "none"
    return _latest_ledger_next_action(run)


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


def _entry_matches_types(entry: dict[str, str], entry_types: list[str] | None) -> bool:
    if not entry_types:
        return True
    allowed = {str(item).strip() for item in entry_types if str(item).strip()}
    return entry.get("type", "") in allowed


def _ledger_entry_public(entry: dict[str, str]) -> dict[str, str]:
    keys = (
        "title",
        "type",
        "status",
        "materiality",
        "statement",
        "refs",
        "next_action",
        "actor",
        "recorded_at",
    )
    return {key: entry.get(key, "") for key in keys if entry.get(key, "")}


def _section_lines(path: Path, heading: str, *, limit: int = 20) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out: list[str] = []
    in_section = False
    for line in lines:
        if line.strip() == heading:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and line.strip():
            out.append(line.strip())
    return out[:limit]


def _entry_counts(entries: list[dict[str, str]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        value = entry.get(key, "") or "unknown"
        counts[value] = counts.get(value, 0) + 1
    return counts


def ledger_status(*, session_id: str | None = None, limit: int = 8) -> dict[str, Any]:
    """Return bounded, model-facing ledger state without raw file rehydration."""

    run = ensure_current_run(session_id=session_id)
    entries = _ledger_entry_summaries(run)
    recent = [_ledger_entry_public(entry) for entry in entries[-max(1, min(limit, 50)):]]
    return {
        "run_id": run.run_id,
        "ledger_path": str(run.ledger_path),
        "objective": _section_lines(run.ledger_path, "## Objective", limit=8),
        "next_action": _latest_ledger_next_action(run),
        "entry_count": len(entries),
        "counts_by_type": _entry_counts(entries, "type"),
        "counts_by_status": _entry_counts(entries, "status"),
        "recent_entries": recent,
        "gaps": [
            _ledger_entry_public(entry)
            for entry in entries
            if entry.get("type") in {"gap", "contradiction", "failure"}
        ][-10:],
    }


def ledger_tail(
    *,
    session_id: str | None = None,
    limit: int = 10,
    entry_types: list[str] | None = None,
) -> dict[str, Any]:
    run = ensure_current_run(session_id=session_id)
    entries = [
        _ledger_entry_public(entry)
        for entry in _ledger_entry_summaries(run)
        if _entry_matches_types(entry, entry_types)
    ]
    bounded = max(1, min(limit, 50))
    return {
        "run_id": run.run_id,
        "ledger_path": str(run.ledger_path),
        "entries": entries[-bounded:],
        "returned": min(len(entries), bounded),
        "total_matching": len(entries),
    }


def ledger_search(
    *,
    query: str,
    session_id: str | None = None,
    limit: int = 10,
    entry_types: list[str] | None = None,
) -> dict[str, Any]:
    run = ensure_current_run(session_id=session_id)
    needle = query.strip().lower()
    matches: list[dict[str, str]] = []
    if needle:
        for entry in _ledger_entry_summaries(run):
            if not _entry_matches_types(entry, entry_types):
                continue
            haystack = "\n".join(str(value) for value in entry.values()).lower()
            if needle in haystack:
                matches.append(_ledger_entry_public(entry))
    bounded = max(1, min(limit, 50))
    return {
        "run_id": run.run_id,
        "ledger_path": str(run.ledger_path),
        "query": query,
        "matches": matches[:bounded],
        "returned": min(len(matches), bounded),
        "total_matching": len(matches),
    }


def artifact_manifest_status(*, session_id: str | None = None) -> dict[str, Any]:
    run = ensure_current_run(session_id=session_id)
    latest = _latest_artifact_blocks(run)
    return {
        "run_id": run.run_id,
        "artifact_manifest_path": str(run.artifact_manifest_path),
        "artifacts": latest,
        "counts_by_status": _entry_counts(latest, "status"),
        "open_artifacts": [
            artifact for artifact in latest
            if artifact.get("status") in {"expected", "missing"}
        ],
    }


def _run_runtime_metadata(run: VestaRun) -> dict[str, str]:
    return {
        "model": _parse_md_field(run.run_md_path, "Model"),
        "provider": _parse_md_field(run.run_md_path, "Provider"),
        "base_url": _parse_md_field(run.run_md_path, "Base URL"),
        "context_length_tokens": _parse_md_field(run.run_md_path, "Context Length Tokens"),
        "delegation_model": _parse_md_field(run.run_md_path, "Delegation Model"),
        "delegation_provider": _parse_md_field(run.run_md_path, "Delegation Provider"),
        "delegation_base_url": _parse_md_field(run.run_md_path, "Delegation Base URL"),
    }


def _run_status_for_run(run: VestaRun) -> dict[str, Any]:
    validator_state = _validator_finalization_state(run)
    worker_state = _worker_finalization_state(run)
    latest_artifacts = _latest_artifact_blocks(run)
    artifacts = {
        "run_id": run.run_id,
        "artifact_manifest_path": str(run.artifact_manifest_path),
        "artifacts": latest_artifacts,
        "counts_by_status": _entry_counts(latest_artifacts, "status"),
        "open_artifacts": [
            artifact for artifact in latest_artifacts
            if artifact.get("status") in {"expected", "missing"}
        ],
    }
    return {
        "run_id": run.run_id,
        "run_dir": str(run.run_dir),
        "workspace_path": run.workspace_path,
        "ledger_path": str(run.ledger_path),
        "artifact_manifest_path": str(run.artifact_manifest_path),
        "finalization_path": str(run.finalization_path),
        "control_plane_path": str(run.control_plane_path),
        "handoff_path": str(run.handoff_path),
        "finalization_status": _finalization_status(run),
        "next_action": _run_next_action(run),
        "runtime": _run_runtime_metadata(run),
        "lineage": _run_lineage_metadata(run),
        "artifacts": artifacts,
        "worker_state": worker_state,
        "validator_status": validator_state.get("status", "absent"),
        "validator_blockers": validator_state.get("blockers", []),
    }


def run_status(*, session_id: str | None = None) -> dict[str, Any]:
    run = ensure_current_run(session_id=session_id)
    return _run_status_for_run(run)


def run_status_from_dir(run_dir: str | os.PathLike[str]) -> dict[str, Any] | None:
    """Return bounded Vesta status for an existing run directory."""

    run = _run_from_dir(run_dir)
    if run is None:
        return None
    return _run_status_for_run(run)


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
    artifacts = _latest_artifact_blocks(run)
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

## Run Lineage

{_render_run_lineage_summary(run)}

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
    control_plane_path = ""
    try:
        control = write_control_plane_snapshot(
            session_id=session_id,
            next_action=resolved_next or None,
        )
        control_plane_path = control.get("control_plane_path", "")
    except Exception:
        control_plane_path = ""
    return {
        "run_id": run.run_id,
        "finalization_path": str(run.finalization_path),
        "control_plane_path": control_plane_path,
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
            f"model lane `{worker.get('model_lane', '')}`, "
            f"child session `{worker.get('child_session_id', '')}`, "
            f"child run `{worker.get('child_run_id', '')}`, "
            f"expected artifacts `{_json_compact(_expected_worker_artifacts(worker))}`"
        )
    if worker_state.get("blockers"):
        lines.append("")
        lines.append("Blockers:")
        lines.extend(f"- {blocker}" for blocker in worker_state["blockers"])
    return "\n".join(lines)


def guard_run_end(
    *,
    objective: str = "",
    exit_reason: str = "",
    final_response: str | None = None,
    last_message_role: str | None = None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Write blocked run state when Hermes exits before Vesta is finalized."""

    run = get_current_run() or _run_from_env()
    if run is None:
        return {"guarded": False, "reason": "no_active_run"}
    if _finalization_status(run) != "not_written":
        return {"guarded": False, "reason": "finalization_already_written"}

    artifacts = _latest_artifact_blocks(run)
    open_artifacts = [
        artifact for artifact in artifacts
        if artifact.get("status") in {"expected", "missing"}
    ]
    ended_on_tool = last_message_role == "tool"
    missing_response = not (final_response or "").strip()
    if not open_artifacts and not ended_on_tool and not missing_response:
        return {"guarded": False, "reason": "no_incomplete_run_state"}

    resolved_objective = (objective or "").strip() or "Complete the active Vesta run."
    next_action = "Continue from the last durable Vesta state and resolve run-end blockers."
    if open_artifacts:
        next_action = "Produce or verify missing artifacts, then finalize the run."
    elif ended_on_tool:
        next_action = "Continue from the last tool result and produce the final response."

    failures: list[str] = []
    if ended_on_tool:
        failures.append("Run ended after a tool result before a final assistant response.")
    if missing_response:
        failures.append("Run ended without a final assistant response.")

    gaps = [
        f"Run-end guard fired because exit_reason=`{exit_reason or 'unknown'}`."
    ]
    if open_artifacts:
        gaps.append(
            "Open artifacts remain: "
            + ", ".join(
                f"{artifact.get('path', '')} ({artifact.get('status', '')})"
                for artifact in open_artifacts
            )
        )

    finalization = write_finalization(
        objective=resolved_objective,
        skip_reason="Run-end guard wrote this packet because normal finalization did not complete.",
        failures=failures,
        gaps=gaps,
        next_action=next_action,
        session_id=session_id,
    )
    control = write_control_plane_snapshot(
        session_id=session_id,
        next_action=next_action,
    )
    handoff = write_handoff(
        objective=resolved_objective,
        completed_work=[],
        next_action=next_action,
        session_id=session_id,
    )
    return {
        "guarded": True,
        "reason": "run_end_incomplete",
        "verdict": finalization["verdict"],
        "blockers": finalization["blockers"],
        "finalization_path": finalization["finalization_path"],
        "control_plane_path": control["control_plane_path"],
        "handoff_path": handoff["handoff_path"],
        "next_action": next_action,
    }


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
