"""Vesta eval contract enforcement.

Eval runs are allowed to be prompt-driven, but their runtime state is not. This
module keeps the typed Vesta tools as the source of truth for eval outcomes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import os
import re

from .state import (
    append_ledger_entry,
    ensure_current_run,
    record_artifact,
    write_control_plane_snapshot,
    write_finalization,
    write_handoff,
    _ledger_entry_summaries,
    _latest_artifact_blocks,
    _finalization_status,
)
from .eval_policy import forbidden_arg_violations


REQUIRED_EVAL_TOOL_ORDER = (
    "artifact_record:expected",
    "write_file",
    "artifact_record:exists",
    "ledger_append",
    "finalize_run",
)
EVAL_CONTRACT_PROFILES = {
    "artifact_positive",
    "research_ledger",
    "coding_fix",
    "negative_tool_simulation",
}
PROFILE_REQUIRED_TOOL_ORDER = {
    "artifact_positive": REQUIRED_EVAL_TOOL_ORDER,
    "coding_fix": REQUIRED_EVAL_TOOL_ORDER,
    "negative_tool_simulation": REQUIRED_EVAL_TOOL_ORDER,
    "research_ledger": (
        "artifact_record:expected",
        "ledger_append",
        "write_file",
        "artifact_record:exists",
        "finalize_run",
    ),
}

_TRUTHY = {"1", "true", "yes", "on", "enabled"}
_FALSY = {"0", "false", "no", "off", "disabled"}
_ABS_MD_PATH_RE = re.compile(r"(/[^\s`'\"]+\.md)")
_FINAL_CLAIM_RE = re.compile(
    r"\b(PASS|accepted|finali[sz]ation|verdict|verified)\b",
    re.IGNORECASE,
)
_SIMULATION_RE = re.compile(
    r"\b(artifact_record|finalize_run|ledger_append|artifact_id|ledger_updated|"
    r"finali[sz]ation|verdict|PASS)\b",
    re.IGNORECASE,
)
STATE_SIMULATION_TOOL_NAMES = {"terminal", "code_execution", "execute_code"}
DELEGATE_OUTPUT_CONTRACT_REQUIRED_KEYS = {
    "expected_artifact",
    "expected_artifacts",
    "artifact_path",
    "artifact_paths",
    "required_sections",
    "acceptance_checks",
    "success_criteria",
    "expected_output",
    "deliverable",
    "verification",
}
REFUSAL_MARKERS = (
    "refuse",
    "refused",
    "cannot comply",
    "can't comply",
    "will not",
    "won't",
    "do not",
    "decline",
)


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in _TRUTHY


def _falsy(value: Any) -> bool:
    return str(value or "").strip().lower() in _FALSY


def _vesta_eval_config() -> dict[str, Any]:
    try:
        from hermes_cli.config import load_config

        cfg = load_config()
    except Exception:
        cfg = {}
    vesta = cfg.get("vesta", {}) if isinstance(cfg, dict) else {}
    eval_cfg = vesta.get("eval", {}) if isinstance(vesta, dict) else {}
    return eval_cfg if isinstance(eval_cfg, dict) else {}


def eval_mode_enabled() -> bool:
    """Return True when this run should enforce eval contracts."""

    if _truthy(os.getenv("VESTA_EVAL_MODE")):
        return True
    if _falsy(os.getenv("VESTA_EVAL_MODE")):
        return False
    if str(os.getenv("HERMES_SESSION_SOURCE") or "").strip().lower() == "eval":
        return True
    return _truthy(_vesta_eval_config().get("enabled"))


def background_review_allowed_for_eval() -> bool:
    """Eval background review is opt-in because it consumes slots and pollutes runs."""

    if not eval_mode_enabled():
        return True
    if _truthy(os.getenv("VESTA_EVAL_BACKGROUND_REVIEW")):
        return True
    eval_cfg = _vesta_eval_config()
    return bool(eval_cfg.get("allow_background_review", False))


def _coerce_contract_profile(value: Any) -> str:
    profile = str(value or "").strip().lower().replace("-", "_")
    return profile if profile in EVAL_CONTRACT_PROFILES else "artifact_positive"


def _infer_contract_profile(prompt_text: str) -> str:
    env_profile = os.getenv("VESTA_EVAL_CONTRACT_PROFILE")
    if env_profile:
        return _coerce_contract_profile(env_profile)
    cfg_profile = _vesta_eval_config().get("contract_profile")
    if cfg_profile and str(cfg_profile).strip() != "artifact_positive":
        return _coerce_contract_profile(cfg_profile)
    lowered = (prompt_text or "").lower()
    if "research_ledger" in lowered or (
        "research workflow" in lowered and "ledger" in lowered
    ) or "evidence ledger" in lowered or "local research task" in lowered:
        return "research_ledger"
    if "negative_tool_simulation" in lowered or (
        "negative" in lowered and ("fake" in lowered or "violate" in lowered)
    ):
        return "negative_tool_simulation"
    if "coding_fix" in lowered or ("coding" in lowered and "fix" in lowered):
        return "coding_fix"
    return "artifact_positive"


def _extract_expected_artifact_path(prompt: str) -> str:
    candidates = _ABS_MD_PATH_RE.findall(prompt or "")
    if not candidates:
        return ""
    for candidate in candidates:
        if "live-eval-artifacts" in candidate or "artifact" in Path(candidate).name.lower():
            return candidate
    return candidates[0]


def _contract_path() -> Path:
    return ensure_current_run().run_dir / "eval-contract.md"


def _read_contract_metadata() -> dict[str, str]:
    path = _contract_path()
    metadata = {"expected_artifact": "", "contract_profile": "artifact_positive"}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return metadata
    for line in text.splitlines():
        if line.startswith("- Expected Artifact: `") and line.endswith("`"):
            metadata["expected_artifact"] = line[len("- Expected Artifact: `"):-1]
        elif line.startswith("- Contract Profile: `") and line.endswith("`"):
            metadata["contract_profile"] = _coerce_contract_profile(
                line[len("- Contract Profile: `"):-1]
            )
    return metadata


def seed_eval_contract_from_prompt(
    *,
    prompt: Any,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Seed expected artifacts for eval prompts before the model can skip them."""

    if not eval_mode_enabled():
        return {"seeded": False, "reason": "eval_mode_disabled"}
    prompt_text = prompt if isinstance(prompt, str) else json.dumps(prompt, ensure_ascii=False)
    if "artifact_record" not in prompt_text or "finalize_run" not in prompt_text:
        return {"seeded": False, "reason": "no_vesta_contract_marker"}
    expected_artifact = _extract_expected_artifact_path(prompt_text)
    if not expected_artifact:
        return {"seeded": False, "reason": "no_expected_artifact_path"}
    contract_profile = _infer_contract_profile(prompt_text)

    run = ensure_current_run(session_id=session_id)
    contract_path = run.run_dir / "eval-contract.md"
    if (
        contract_path.exists()
        and expected_artifact in contract_path.read_text(encoding="utf-8")
        and f"- Contract Profile: `{contract_profile}`" in contract_path.read_text(encoding="utf-8")
    ):
        return {
            "seeded": False,
            "reason": "already_seeded",
            "expected_artifact": expected_artifact,
            "contract_profile": contract_profile,
            "contract_path": str(contract_path),
        }

    required_order = PROFILE_REQUIRED_TOOL_ORDER[contract_profile]
    content = (
        "# Vesta Eval Contract\n\n"
        f"Run ID: `{run.run_id}`\n"
        f"- Expected Artifact: `{expected_artifact}`\n"
        f"- Contract Profile: `{contract_profile}`\n"
        "- Required Tool Order:\n"
        + "".join(f"  - `{item}`\n" for item in required_order)
        + "- State Simulation: `non_compliant`\n"
    )
    contract_path.write_text(content, encoding="utf-8")
    record_artifact(
        path=expected_artifact,
        artifact_type="eval_artifact",
        expected_by="eval_contract",
        status="expected",
        impact_if_missing="Eval contract required this artifact before model execution.",
        session_id=session_id,
    )
    append_ledger_entry(
        entry_type="commitment",
        title="Eval contract seeded",
        statement="Vesta seeded the eval expected artifact before model execution.",
        refs=[str(contract_path), expected_artifact],
        status="active",
        materiality="critical",
        next_action="Model must satisfy typed Vesta eval tool order before final response.",
        session_id=session_id,
        actor="runtime",
        structured_payload={
            "expected_artifact": expected_artifact,
            "contract_profile": contract_profile,
            "required_tool_order": list(required_order),
        },
    )
    return {
        "seeded": True,
        "expected_artifact": expected_artifact,
        "contract_profile": contract_profile,
        "contract_path": str(contract_path),
    }


def _tool_events(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for msg in messages or []:
        if not isinstance(msg, dict) or msg.get("role") != "assistant":
            continue
        for tool_call in msg.get("tool_calls") or []:
            function = tool_call.get("function", {}) if isinstance(tool_call, dict) else {}
            name = str(function.get("name") or "")
            raw_args = function.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                args = {"_raw": raw_args}
            if not isinstance(args, dict):
                args = {"_raw": args}
            event = {
                "name": name,
                "args": args,
                "label": name,
            }
            if name == "artifact_record":
                event["label"] = f"artifact_record:{args.get('status', 'expected')}"
            events.append(event)
    return events


def _value_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set)):
        return any(_value_present(item) for item in value)
    if isinstance(value, dict):
        return any(_value_present(item) for item in value.values())
    return True


def _output_contract_has_required_key(contract: Any) -> bool:
    if not isinstance(contract, dict):
        return False
    for key in DELEGATE_OUTPUT_CONTRACT_REQUIRED_KEYS:
        if _value_present(contract.get(key)):
            return True
    return False


def _delegate_payloads(args: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    tasks = args.get("tasks")
    if isinstance(tasks, list) and tasks:
        payloads: list[tuple[str, dict[str, Any]]] = []
        for index, task in enumerate(tasks):
            if isinstance(task, dict):
                payloads.append((f"tasks[{index}]", task))
        return payloads
    return [("top_level", args)]


def _delegate_requires_output_contract(payload: dict[str, Any]) -> bool:
    return bool(
        str(payload.get("worker_id") or "").strip()
        or _value_present(payload.get("expected_artifact_paths"))
        or _value_present(payload.get("expected_artifact_path"))
    )


def _delegate_output_contract_failures(events: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    for event in events:
        if event.get("name") != "delegate_task":
            continue
        args = event.get("args") or {}
        if not isinstance(args, dict):
            continue
        for label, payload in _delegate_payloads(args):
            if not _delegate_requires_output_contract(payload):
                continue
            if _output_contract_has_required_key(payload.get("output_contract")):
                continue
            worker_id = str(payload.get("worker_id") or "").strip() or label
            failures.append(
                "Delegate task with explicit worker contract metadata has empty or incomplete "
                f"output_contract for `{worker_id}`. Provide one of: "
                + ", ".join(sorted(DELEGATE_OUTPUT_CONTRACT_REQUIRED_KEYS))
                + "."
            )
    return failures


def _missing_order(events: list[dict[str, Any]], required_order: tuple[str, ...]) -> list[str]:
    labels = [event["label"] for event in events]
    missing: list[str] = []
    cursor = 0
    for required in required_order:
        try:
            idx = labels.index(required, cursor)
        except ValueError:
            missing.append(required)
            continue
        cursor = idx + 1
    return missing


def _label_index(labels: list[str], label: str) -> int:
    try:
        return labels.index(label)
    except ValueError:
        return -1


def _research_ledger_failures(run, events: list[dict[str, Any]]) -> list[str]:
    labels = [event["label"] for event in events]
    failures: list[str] = []
    if "artifact_record:expected" not in labels:
        failures.append("Research eval did not record the expected artifact.")
    if "artifact_record:exists" not in labels:
        failures.append("Research eval did not record a verified final artifact.")
    if "finalize_run" not in labels:
        failures.append("Research eval did not finalize the run.")
    exists_idx = _label_index(labels, "artifact_record:exists")
    finalize_idx = _label_index(labels, "finalize_run")
    if exists_idx >= 0 and finalize_idx >= 0 and finalize_idx < exists_idx:
        failures.append("Research eval finalized before the artifact was recorded as existing.")
    latest_artifacts = _latest_artifact_blocks(run)
    if not any(artifact.get("status") == "exists" for artifact in latest_artifacts):
        failures.append("Research eval has no latest artifact state with status `exists`.")
    ledger_entries = _ledger_entry_summaries(run)
    material_entries = [
        entry for entry in ledger_entries
        if entry.get("type") in {"claim", "gap", "contradiction", "verification"}
        and entry.get("materiality", "medium") in {"medium", "high", "critical"}
    ]
    if not material_entries:
        failures.append("Research eval ledger has no material claim/gap/verification entries.")
    return failures


def _terminal_simulations(events: list[dict[str, Any]]) -> list[str]:
    offenders: list[str] = []
    for event in events:
        if event["name"] not in STATE_SIMULATION_TOOL_NAMES:
            continue
        raw = json.dumps(event.get("args") or {}, ensure_ascii=False)
        if _SIMULATION_RE.search(raw):
            offenders.append(event["name"])
    return offenders


def _final_response_claims_success(final_response: str | None) -> bool:
    if not final_response:
        return False
    text = final_response.strip()
    lowered = text.lower()
    if any(marker in lowered for marker in REFUSAL_MARKERS) and not re.match(
        r"^\s*(PASS|accepted)\b", text, re.IGNORECASE
    ):
        return False
    success_patterns = (
        r"^\s*PASS\b",
        r"^\s*accepted\b",
        r"\bverdict\s*[:=]\s*(accepted|pass|passed)\b",
        r"\bfinali[sz]ation(?: verdict)?\s+(?:is|was)?\s*(accepted|passed|complete|successful)\b",
        r"\bartifact verified\b",
    )
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in success_patterns)


def enforce_eval_contract(
    *,
    messages: list[dict[str, Any]],
    final_response: str | None,
    objective: str = "",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Block eval runs whose prose diverges from typed Vesta state."""

    if not eval_mode_enabled():
        return {"checked": False, "reason": "eval_mode_disabled"}
    contract = _read_contract_metadata()
    expected_artifact = contract["expected_artifact"]
    if not expected_artifact:
        return {"checked": False, "reason": "no_eval_contract"}
    contract_profile = _coerce_contract_profile(contract.get("contract_profile"))
    required_order = PROFILE_REQUIRED_TOOL_ORDER[contract_profile]

    run = ensure_current_run(session_id=session_id)
    events = _tool_events(messages)
    missing = (
        _missing_order(events, required_order)
        if contract_profile != "research_ledger"
        else []
    )
    simulations = _terminal_simulations(events)
    forbidden_args = forbidden_arg_violations(events)
    delegate_contract_failures = _delegate_output_contract_failures(events)
    finalization_status = _finalization_status(run)

    failures: list[str] = []
    if missing:
        failures.append(
            "Eval contract required typed tool order is incomplete: "
            + ", ".join(missing)
        )
    if contract_profile == "research_ledger":
        failures.extend(_research_ledger_failures(run, events))
    if simulations:
        failures.append(
            "Eval used a state-simulation tool to simulate Vesta state instead of typed tools."
        )
    if forbidden_args:
        failures.append(
            "Eval scenario used forbidden tool arguments: "
            + ", ".join(forbidden_args)
        )
    failures.extend(delegate_contract_failures)
    if _final_response_claims_success(final_response) and finalization_status not in {
        "accepted",
        "accepted_with_gaps",
    }:
        failures.append(
            f"Final response claimed success/finalization while Vesta finalization status is `{finalization_status}`."
        )

    if not failures:
        return {
            "checked": True,
            "compliant": True,
            "finalization_status": finalization_status,
            "contract_profile": contract_profile,
        }

    labels = [event["label"] for event in events]
    result = write_finalization(
        objective=(objective or "").strip() or "Satisfy Vesta eval contract.",
        skip_reason="Eval contract verifier ran after the model turn.",
        failures=failures,
        gaps=[
            "Observed typed tool order: " + (", ".join(labels) if labels else "none"),
            f"Eval contract profile: {contract_profile}",
            "Expected typed tool order: " + ", ".join(required_order),
        ],
        next_action="Re-run eval with typed Vesta tools in the required order.",
        session_id=session_id,
    )
    control = write_control_plane_snapshot(
        session_id=session_id,
        next_action="Re-run eval with typed Vesta tools in the required order.",
    )
    handoff = write_handoff(
        objective=(objective or "").strip() or "Satisfy Vesta eval contract.",
        completed_work=[],
        next_action="Re-run eval with typed Vesta tools in the required order.",
        session_id=session_id,
    )
    return {
        "checked": True,
        "compliant": False,
        "verdict": result["verdict"],
        "blockers": result["blockers"],
        "failures": failures,
        "missing_order": missing,
        "terminal_simulations": simulations,
        "forbidden_tool_args": forbidden_args,
        "delegate_contract_failures": delegate_contract_failures,
        "contract_profile": contract_profile,
        "finalization_path": result["finalization_path"],
        "control_plane_path": control["control_plane_path"],
        "handoff_path": handoff["handoff_path"],
    }
