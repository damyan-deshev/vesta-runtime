"""Copied-workspace coding eval support for Vesta runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import difflib
import hashlib
import json
import os
import shutil
import uuid

from agent.redact import redact_sensitive_text

from .state import (
    append_ledger_entry,
    capture_raw_output,
    ensure_current_run,
    record_artifact,
)


DEFAULT_EXCLUDED_PATHS = [
    ".git",
    ".hg",
    ".svn",
    ".env",
    ".env.local",
    ".venv",
    "venv",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    ".worktrees",
    ".hermes",
    "dist",
    "build",
]


def _new_eval_id() -> str:
    return f"eval_{uuid.uuid4().hex[:10]}"


def _json_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "<redacted>" if _looks_secret_key(str(key)) else _redact_payload(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_payload(item) for item in value]
    if isinstance(value, str):
        return redact_sensitive_text(value)
    return value


def _looks_secret_key(key: str) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in ("api_key", "apikey", "token", "secret", "password"))


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def _normalize_exclusions(
    excluded_paths: list[str] | None,
    *,
    include_sensitive_paths: bool,
) -> list[str]:
    exclusions = [] if include_sensitive_paths else list(DEFAULT_EXCLUDED_PATHS)
    exclusions.extend(path for path in (excluded_paths or []) if path)
    seen: set[str] = set()
    unique: list[str] = []
    for path in exclusions:
        norm = path.strip().strip("/")
        if norm and norm not in seen:
            unique.append(norm)
            seen.add(norm)
    return unique


def _copy_ignore(excluded_paths: list[str]):
    excluded_names = {path for path in excluded_paths if "/" not in path}
    excluded_rel = {Path(path) for path in excluded_paths if "/" in path}

    def ignore(src: str, names: list[str]) -> set[str]:
        src_path = Path(src)
        ignored: set[str] = set()
        for name in names:
            if name in excluded_names:
                ignored.add(name)
                continue
            candidate = src_path / name
            for rel in excluded_rel:
                if candidate.match(str(rel)) or name == rel.name:
                    ignored.add(name)
                    break
        return ignored

    return ignore


def start_coding_eval(
    *,
    original_workspace: str,
    prompt: str,
    model: str = "",
    provider: str = "",
    config: dict[str, Any] | None = None,
    excluded_paths: list[str] | None = None,
    include_sensitive_paths: bool = False,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Create an isolated copied workspace and record eval seed state."""

    run = ensure_current_run(session_id=session_id)
    original = Path(original_workspace).expanduser().resolve()
    if not original.exists() or not original.is_dir():
        raise ValueError(f"original_workspace must be an existing directory: {original_workspace}")

    eval_id = _new_eval_id()
    eval_dir = run.run_dir / "evals" / eval_id
    eval_workspace = eval_dir / "workspace"
    if _path_is_within(eval_workspace, original):
        raise ValueError("eval workspace must not be inside original workspace")
    eval_dir.mkdir(parents=True, exist_ok=False)

    exclusions = _normalize_exclusions(excluded_paths, include_sensitive_paths=include_sensitive_paths)
    shutil.copytree(original, eval_workspace, ignore=_copy_ignore(exclusions), symlinks=True)

    prompt_ref = capture_raw_output(
        content=redact_sensitive_text(prompt),
        source="coding_eval_prompt",
        tool_use_id=f"{eval_id}_prompt",
        session_id=session_id,
    )
    safe_config = _redact_payload({
        "model": model,
        "provider": provider,
        "config": config or {},
        "include_sensitive_paths": include_sensitive_paths,
        "excluded_paths": exclusions,
    })
    config_ref = capture_raw_output(
        content=_json_compact(safe_config),
        source="coding_eval_config",
        tool_use_id=f"{eval_id}_config",
        session_id=session_id,
    )

    eval_md = eval_dir / "eval.md"
    eval_md.write_text(
        f"""# Vesta Coding Eval

Eval ID: `{eval_id}`
Original Workspace: `{original}`
Eval Workspace: `{eval_workspace}`
Prompt Ref: `{prompt_ref['raw_ref']}`
Config Ref: `{config_ref['raw_ref']}`
Model: `{redact_sensitive_text(model)}`
Provider: `{redact_sensitive_text(provider)}`
Included Sensitive Paths: `{include_sensitive_paths}`
Excluded Paths: `{', '.join(exclusions)}`
Final Verdict: `pending`

## Verification

- pending

## Diff

- pending
""",
        encoding="utf-8",
    )

    record_artifact(
        path=str(eval_md),
        artifact_type="eval",
        expected_by="run_path",
        status="exists",
        session_id=session_id,
    )
    append_ledger_entry(
        entry_type="action",
        title="Coding eval workspace created",
        statement=f"Copied `{original}` to isolated eval workspace `{eval_workspace}`.",
        refs=[str(eval_md), prompt_ref["raw_ref"], config_ref["raw_ref"]],
        status="active",
        materiality="high",
        session_id=session_id,
        actor="runtime",
        structured_payload={
            "eval_id": eval_id,
            "original_workspace": str(original),
            "eval_workspace": str(eval_workspace),
            "excluded_paths": exclusions,
        },
    )
    return {
        "eval_id": eval_id,
        "eval_dir": str(eval_dir),
        "eval_workspace": str(eval_workspace),
        "eval_md_path": str(eval_md),
        "prompt_ref": prompt_ref["raw_ref"],
        "config_ref": config_ref["raw_ref"],
        "excluded_paths": exclusions,
    }


def capture_coding_eval_result(
    *,
    eval_id: str,
    verification_command: str,
    verification_exit_status: int,
    verification_output: str,
    failure_reason: str = "",
    skip_reason: str = "",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Capture diff and verification output for a copied-workspace eval."""

    run = ensure_current_run(session_id=session_id)
    eval_dir = run.run_dir / "evals" / eval_id
    eval_md = eval_dir / "eval.md"
    if not eval_md.exists():
        raise ValueError(f"Unknown coding eval id: {eval_id}")

    metadata = _read_eval_metadata(eval_md)
    original = Path(metadata["original_workspace"])
    eval_workspace = Path(metadata["eval_workspace"])
    excluded_paths = [
        part.strip() for part in metadata.get("excluded_paths", "").split(",") if part.strip()
    ]
    diff_text = _workspace_diff(original, eval_workspace, excluded_paths)
    diff_ref = capture_raw_output(
        content=diff_text or "No workspace diff detected.\n",
        source="coding_eval_diff",
        tool_use_id=f"{eval_id}_diff",
        session_id=session_id,
    )
    verification_ref = capture_raw_output(
        content=redact_sensitive_text(verification_output),
        source="coding_eval_verification",
        tool_use_id=f"{eval_id}_verification",
        session_id=session_id,
        metadata={
            "command": redact_sensitive_text(verification_command),
            "exit_status": verification_exit_status,
        },
    )

    verdict = _eval_verdict(
        verification_exit_status=verification_exit_status,
        failure_reason=failure_reason,
        skip_reason=skip_reason,
    )
    blockers = []
    if verification_exit_status != 0 and not failure_reason and not skip_reason:
        blockers.append("failed_verification_without_reason")

    _append_eval_result(
        eval_md=eval_md,
        verification_command=verification_command,
        verification_exit_status=verification_exit_status,
        verification_ref=verification_ref["raw_ref"],
        diff_ref=diff_ref["raw_ref"],
        verdict=verdict,
        failure_reason=failure_reason,
        skip_reason=skip_reason,
        blockers=blockers,
    )
    append_ledger_entry(
        entry_type="verification" if verdict != "blocked" else "failure",
        title=f"Coding eval {verdict}",
        statement=(
            f"Coding eval `{eval_id}` recorded verification exit status "
            f"`{verification_exit_status}` with verdict `{verdict}`."
        ),
        refs=[str(eval_md), diff_ref["raw_ref"], verification_ref["raw_ref"]],
        status=verdict,
        materiality="critical",
        next_action="Record failure or skip reason before accepting eval." if blockers else None,
        session_id=session_id,
        actor="runtime",
        structured_payload={"eval_id": eval_id, "blockers": blockers},
    )
    return {
        "eval_id": eval_id,
        "eval_md_path": str(eval_md),
        "diff_ref": diff_ref["raw_ref"],
        "verification_ref": verification_ref["raw_ref"],
        "verdict": verdict,
        "blockers": blockers,
    }


def _read_eval_metadata(eval_md: Path) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in eval_md.read_text(encoding="utf-8").splitlines():
        if ": `" not in line:
            continue
        key, _, value = line.partition(": `")
        if value.endswith("`"):
            value = value[:-1]
        metadata[key.lower().replace(" ", "_")] = value
    return metadata


def _eval_verdict(*, verification_exit_status: int, failure_reason: str, skip_reason: str) -> str:
    if verification_exit_status == 0:
        return "accepted"
    if skip_reason:
        return "accepted_with_gaps"
    if failure_reason:
        return "failed"
    return "blocked"


def _append_eval_result(
    *,
    eval_md: Path,
    verification_command: str,
    verification_exit_status: int,
    verification_ref: str,
    diff_ref: str,
    verdict: str,
    failure_reason: str,
    skip_reason: str,
    blockers: list[str],
) -> None:
    with eval_md.open("a", encoding="utf-8") as f:
        f.write(
            "\n## Captured Result\n\n"
            f"- Verification Command: `{redact_sensitive_text(verification_command)}`\n"
            f"- Verification Exit Status: `{verification_exit_status}`\n"
            f"- Verification Ref: `{verification_ref}`\n"
            f"- Diff Ref: `{diff_ref}`\n"
            f"- Final Verdict: `{verdict}`\n"
            f"- Failure Reason: {redact_sensitive_text(failure_reason) if failure_reason else ''}\n"
            f"- Skip Reason: {redact_sensitive_text(skip_reason) if skip_reason else ''}\n"
            f"- Blockers: `{_json_compact(blockers)}`\n"
        )


def _workspace_diff(original: Path, eval_workspace: Path, excluded_paths: list[str]) -> str:
    original_files = _file_map(original, excluded_paths)
    eval_files = _file_map(eval_workspace, excluded_paths)
    lines: list[str] = []
    for rel in sorted(set(original_files) | set(eval_files)):
        left = original_files.get(rel)
        right = eval_files.get(rel)
        if left == right:
            continue
        if left is None:
            lines.append(f"Added: {rel}\n")
            lines.extend(_render_added_file(eval_workspace / rel))
            continue
        if right is None:
            lines.append(f"Deleted: {rel}\n")
            continue
        lines.extend(_file_diff(original / rel, eval_workspace / rel, rel))
    return "".join(lines)


def _file_map(root: Path, excluded_paths: list[str]) -> dict[Path, str]:
    result: dict[Path, str] = {}
    excluded = {Path(path) for path in excluded_paths}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if _is_excluded(rel, excluded):
            continue
        result[rel] = _file_fingerprint(path)
    return result


def _is_excluded(rel: Path, excluded: set[Path]) -> bool:
    parts = set(rel.parts)
    for item in excluded:
        if len(item.parts) == 1 and item.name in parts:
            return True
        try:
            rel.relative_to(item)
            return True
        except ValueError:
            continue
    return False


def _file_fingerprint(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return "unreadable"


def _file_diff(original: Path, modified: Path, rel: Path) -> list[str]:
    try:
        left = original.read_text(encoding="utf-8").splitlines(keepends=True)
        right = modified.read_text(encoding="utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        return [f"Binary changed: {rel}\n"]
    return list(
        difflib.unified_diff(
            left,
            right,
            fromfile=f"original/{rel}",
            tofile=f"eval/{rel}",
        )
    )


def _render_added_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        return [f"Binary added: {path.name}\n"]
    return list(difflib.unified_diff([], text, fromfile="/dev/null", tofile=f"eval/{path.name}"))
