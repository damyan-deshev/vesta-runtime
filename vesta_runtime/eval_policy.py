"""Eval-only Vesta fixture and override policy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os
import re


_TRUTHY = {"1", "true", "yes", "on", "enabled"}
TYPED_TOOL_PROXY_BYPASS_TOOLS = (
    "read_file",
    "search_files",
    "write_file",
    "patch",
    "ledger_append",
    "artifact_record",
    "finalize_run",
    "run_status",
    "ledger_status",
    "artifact_manifest_status",
)


@dataclass(frozen=True)
class EvalPolicy:
    enabled: bool
    read_only_fixture_paths: tuple[str, ...] = ()
    forbidden_write_paths: tuple[str, ...] = ()
    forbidden_tool_args: tuple[str, ...] = ()


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in _TRUTHY


def _split_csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _as_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return _split_csv(value)
    if isinstance(value, (list, tuple)):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return ()


def _vesta_eval_config() -> dict[str, Any]:
    try:
        from hermes_cli.config import load_config

        cfg = load_config()
    except Exception:
        cfg = {}
    vesta = cfg.get("vesta", {}) if isinstance(cfg, dict) else {}
    eval_cfg = vesta.get("eval", {}) if isinstance(vesta, dict) else {}
    return eval_cfg if isinstance(eval_cfg, dict) else {}


def load_eval_policy() -> EvalPolicy:
    cfg = _vesta_eval_config()
    enabled = (
        _truthy(os.getenv("VESTA_EVAL_MODE"))
        or str(os.getenv("HERMES_SESSION_SOURCE") or "").strip().lower() == "eval"
        or _truthy(cfg.get("enabled"))
    )
    read_only = (
        _split_csv(os.getenv("VESTA_EVAL_READ_ONLY_PATHS"))
        or _as_tuple(cfg.get("read_only_fixture_paths"))
    )
    forbidden_writes = (
        _split_csv(os.getenv("VESTA_EVAL_FORBIDDEN_WRITE_PATHS"))
        or _as_tuple(cfg.get("forbidden_write_paths"))
    )
    forbidden_args = (
        _split_csv(os.getenv("VESTA_EVAL_FORBIDDEN_TOOL_ARGS"))
        or _as_tuple(cfg.get("forbidden_tool_args"))
    )
    return EvalPolicy(
        enabled=enabled,
        read_only_fixture_paths=read_only,
        forbidden_write_paths=forbidden_writes,
        forbidden_tool_args=forbidden_args,
    )


def _resolve(path: str) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        candidate = Path(os.getenv("TERMINAL_CWD") or os.getcwd()) / candidate
    return candidate.resolve(strict=False)


def _path_matches(candidate: Path, policy_path: str) -> bool:
    if not policy_path.strip():
        return False
    root = _resolve(policy_path)
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return candidate == root


def write_path_violation(path: str) -> str:
    policy = load_eval_policy()
    if not policy.enabled:
        return ""
    candidate = _resolve(path)
    for blocked in (*policy.read_only_fixture_paths, *policy.forbidden_write_paths):
        if _path_matches(candidate, blocked):
            return (
                "Vesta eval fixture policy blocked this write/patch path: "
                f"{path}. The scenario declares it read-only or forbidden."
            )
    return ""


def forbidden_arg_violations(events: list[dict[str, Any]]) -> list[str]:
    policy = load_eval_policy()
    if not policy.enabled or not policy.forbidden_tool_args:
        return []
    violations: list[str] = []
    for event in events:
        args = event.get("args") or {}
        if not isinstance(args, dict):
            continue
        tool = str(event.get("name") or "")
        for item in policy.forbidden_tool_args:
            if "." in item:
                expected_tool, arg_name = item.split(".", 1)
                if expected_tool and expected_tool != tool:
                    continue
            else:
                arg_name = item
            if arg_name not in args:
                continue
            value = args.get(arg_name)
            if value not in (None, "", False, [], {}):
                label = f"{tool}.{arg_name}" if tool else arg_name
                if label not in violations:
                    violations.append(label)
    return violations


def typed_tool_proxy_violation(tool_name: str, args: dict[str, Any]) -> str:
    """Return an eval violation when code/terminal proxies typed Vesta tools."""

    policy = load_eval_policy()
    if not policy.enabled:
        return ""
    text = ""
    if tool_name == "execute_code":
        text = str(args.get("code") or "")
    elif tool_name == "terminal":
        text = str(args.get("command") or "")
    else:
        return ""
    if "hermes_tools" not in text:
        return ""
    for proxied_tool in TYPED_TOOL_PROXY_BYPASS_TOOLS:
        pattern = rf"\b{re.escape(proxied_tool)}\s*\("
        import_pattern = rf"from\s+hermes_tools\s+import\b[^\n#]*\b{re.escape(proxied_tool)}\b"
        if re.search(pattern, text) or re.search(import_pattern, text):
            return (
                "Vesta eval policy blocks proxying typed runtime/file tools "
                f"through {tool_name}: use `{proxied_tool}` directly or record "
                "a gap instead."
            )
    return ""


def typed_tool_proxy_violations(events: list[dict[str, Any]]) -> list[str]:
    violations: list[str] = []
    for event in events:
        args = event.get("args") or {}
        if not isinstance(args, dict):
            continue
        violation = typed_tool_proxy_violation(str(event.get("name") or ""), args)
        if violation and violation not in violations:
            violations.append(violation)
    return violations
