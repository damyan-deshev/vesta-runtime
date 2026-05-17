"""Vesta runtime tools."""

from __future__ import annotations

import json
import os

from tools.registry import registry
from vesta_runtime import (
    append_ledger_entry,
    artifact_manifest_status,
    capture_coding_eval_result,
    ledger_search,
    ledger_status,
    ledger_tail,
    process_document,
    purge_raw_ref,
    record_artifact,
    record_validator_result,
    record_worker_state,
    start_coding_eval,
    run_status,
    write_control_plane_snapshot,
    write_finalization,
    write_handoff,
    write_research_artifact_section,
)


def _note_runtime_progress(kind: str) -> None:
    try:
        from tools.tool_output_limits import note_vesta_runtime_progress

        note_vesta_runtime_progress(kind)
    except Exception:
        pass


LEDGER_APPEND_SCHEMA = {
    "name": "ledger_append",
    "description": (
        "Append one small material-state entry to the active Vesta ledger. "
        "Use after material claims, decisions, gaps, failures, artifacts, "
        "worker updates, checkpoints, or next-action changes. Do not use for "
        "trivial mechanics."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "entry_type": {
                "type": "string",
                "enum": [
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
                ],
                "description": "Kind of durable runtime state being recorded.",
            },
            "title": {
                "type": "string",
                "description": "Short entry title.",
            },
            "statement": {
                "type": "string",
                "description": "One concise statement of the fact, decision, gap, or action.",
            },
            "refs": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional source, raw, artifact, or path refs.",
            },
            "status": {
                "type": "string",
                "description": "Entry status such as active, supported, unresolved, accepted, rejected, or superseded.",
            },
            "materiality": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"],
                "description": "Impact if this entry is wrong or lost.",
            },
            "next_action": {
                "type": "string",
                "description": "Optional next action if this entry changes task pressure.",
            },
            "structured_payload": {
                "type": "object",
                "description": "Optional small structured data. Do not paste large raw outputs.",
            },
        },
        "required": ["entry_type", "title", "statement"],
    },
}

LEDGER_STATUS_SCHEMA = {
    "name": "ledger_status",
    "description": (
        "Return bounded structured Vesta ledger status for the active run: "
        "objective, next action, counts, recent entries, and open gaps. "
        "Use this instead of read_file on ledger.md for runtime-state checks."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Maximum recent ledger entries to return, capped by the tool.",
            },
        },
    },
}

LEDGER_TAIL_SCHEMA = {
    "name": "ledger_tail",
    "description": (
        "Return the most recent bounded ledger entries for the active Vesta run. "
        "Use for resume/recovery instead of broad-reading ledger.md."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Maximum entries to return."},
            "entry_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional ledger entry types to include.",
            },
        },
    },
}

LEDGER_SEARCH_SCHEMA = {
    "name": "ledger_search",
    "description": "Search active Vesta ledger entries without returning the raw ledger file.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Case-insensitive text query."},
            "limit": {"type": "integer", "description": "Maximum matching entries to return."},
            "entry_types": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional ledger entry types to include.",
            },
        },
        "required": ["query"],
    },
}

ARTIFACT_MANIFEST_STATUS_SCHEMA = {
    "name": "artifact_manifest_status",
    "description": (
        "Return latest artifact state for the active Vesta run without raw "
        "manifest rehydration. Includes open expected/missing artifacts."
    ),
    "parameters": {"type": "object", "properties": {}},
}

RUN_STATUS_SCHEMA = {
    "name": "run_status",
    "description": (
        "Return bounded structured status for the active Vesta run: paths, "
        "finalization, lineage, artifact state, worker state, validator status, "
        "blockers, and next action."
    ),
    "parameters": {"type": "object", "properties": {}},
}

WHOLE_DOCUMENT_READ_SCHEMA = {
    "name": "whole_document_read",
    "description": (
        "Process a text document for complete coverage by chunking it into raw "
        "refs, appending document chunk findings to the Vesta ledger, and "
        "returning rolling recap context. Use when the task truly requires "
        "whole-document understanding."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the text document to process.",
            },
            "objective": {
                "type": "string",
                "description": "What the complete document read is meant to answer.",
            },
        },
        "required": ["path", "objective"],
    },
}

ARTIFACT_RECORD_SCHEMA = {
    "name": "artifact_record",
    "description": "Record an expected or produced artifact in the active Vesta run manifest.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Artifact path or planned path."},
            "artifact_type": {"type": "string", "description": "Artifact kind, such as report, patch, handoff, eval, or document."},
            "expected_by": {"type": "string", "description": "Why this artifact is expected: user_request, model_commitment, worker_contract, or run_path."},
            "status": {"type": "string", "enum": ["expected", "exists", "missing", "superseded", "purged"], "description": "Current artifact status. Local paths recorded as exists are filesystem-verified by Vesta."},
            "impact_if_missing": {"type": "string", "description": "Why missing this artifact matters."},
        },
        "required": ["path", "artifact_type", "expected_by"],
    },
}

FINALIZE_RUN_SCHEMA = {
    "name": "finalize_run",
    "description": "Write Vesta finalization from recorded run state and return the verdict.",
    "parameters": {
        "type": "object",
        "properties": {
            "objective": {"type": "string", "description": "Run objective being finalized."},
            "verification": {"type": "string", "description": "Verification evidence summary, if performed."},
            "skip_reason": {"type": "string", "description": "Reason verification was skipped, if applicable."},
            "unsupported_claims": {"type": "array", "items": {"type": "string"}},
            "failures": {"type": "array", "items": {"type": "string"}},
            "contradictions": {"type": "array", "items": {"type": "string"}},
            "gaps": {"type": "array", "items": {"type": "string"}},
            "next_action": {"type": "string"},
        },
        "required": ["objective"],
    },
}

WORKER_STATE_RECORD_SCHEMA = {
    "name": "worker_state_record",
    "description": (
        "Record requested, accepted, rejected, running, completed, failed, truncated, "
        "or cancelled worker state in the active Vesta run. Use this around "
        "delegated work so parent acceptance and finalization can inspect "
        "worker artifacts, gaps, failures, material claims, and model lane."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "worker_id": {"type": "string", "description": "Stable worker/subagent id."},
            "objective": {"type": "string", "description": "Worker objective or scope."},
            "status": {
                "type": "string",
                "enum": ["requested", "accepted", "rejected", "running", "completed", "failed", "truncated", "cancelled"],
                "description": "Current worker status.",
            },
            "model_lane": {
                "type": "string",
                "description": "Config-driven model/provider lane, without secrets.",
            },
            "output_contract": {
                "type": "object",
                "description": "Expected output contract, such as expected_artifact or required sections.",
            },
            "child_session_id": {"type": "string", "description": "Child Hermes session id, if known."},
            "child_run_id": {"type": "string", "description": "Child Vesta run id, if known."},
            "expected_artifact_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Artifact paths the worker contract expects, separate from observed artifacts.",
            },
            "artifact_paths": {"type": "array", "items": {"type": "string"}},
            "failures": {"type": "array", "items": {"type": "string"}},
            "gaps": {"type": "array", "items": {"type": "string"}},
            "material_claims": {
                "type": "array",
                "items": {},
                "description": "Material worker claims. Prefer objects with statement and refs.",
            },
            "parent_acceptance": {
                "type": "string",
                "enum": ["unreviewed", "accepted", "rejected", "needs_audit"],
                "description": "Parent acceptance status after spot audit.",
            },
            "spot_audit": {"type": "string", "description": "Short parent audit note for material worker claims."},
            "next_action": {"type": "string", "description": "Next action for this worker state."},
        },
        "required": ["worker_id", "objective", "status", "model_lane"],
    },
}

CODING_EVAL_START_SCHEMA = {
    "name": "coding_eval_start",
    "description": (
        "Create an isolated copied workspace for a coding eval and record "
        "prompt/config/exclusion refs in the active Vesta run."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "original_workspace": {"type": "string", "description": "Directory to copy from."},
            "prompt": {"type": "string", "description": "Eval prompt or task objective."},
            "model": {"type": "string", "description": "Model name, without secrets."},
            "provider": {"type": "string", "description": "Provider name, without secrets."},
            "config": {"type": "object", "description": "Small config metadata; secrets are redacted."},
            "excluded_paths": {"type": "array", "items": {"type": "string"}},
            "include_sensitive_paths": {
                "type": "boolean",
                "description": "Deliberate override to include normally excluded sensitive paths.",
            },
        },
        "required": ["original_workspace", "prompt"],
    },
}

CODING_EVAL_CAPTURE_SCHEMA = {
    "name": "coding_eval_capture",
    "description": (
        "Capture diff and verification output for a Vesta copied-workspace "
        "coding eval, storing full evidence as raw refs."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "eval_id": {"type": "string"},
            "verification_command": {"type": "string"},
            "verification_exit_status": {"type": "integer"},
            "verification_output": {"type": "string"},
            "failure_reason": {
                "type": "string",
                "description": "Required when verification fails and this is not an intentional skip.",
            },
            "skip_reason": {
                "type": "string",
                "description": "Reason verification was intentionally skipped or incomplete.",
            },
        },
        "required": ["eval_id", "verification_command", "verification_exit_status", "verification_output"],
    },
}

RAW_REF_PURGE_SCHEMA = {
    "name": "raw_ref_purge",
    "description": (
        "Delete a Vesta raw payload while preserving its raw/index.md manifest "
        "entry as purged or missing."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "raw_ref": {"type": "string", "description": "Relative raw ref such as raw/tool_1.txt."},
            "reason": {"type": "string", "description": "Why the payload is being purged."},
        },
        "required": ["raw_ref"],
    },
}

VALIDATOR_RESULT_RECORD_SCHEMA = {
    "name": "validator_result_record",
    "description": (
        "Record a selective validator result without requiring an always-on "
        "validator engine. Keeps primary output, tests, and validator findings "
        "separate for finalization."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "trigger": {"type": "string", "description": "Why validation was considered."},
            "scope": {"type": "string", "description": "What output or risk was validated."},
            "mode": {
                "type": "string",
                "enum": ["deterministic", "model", "manual", "skipped"],
            },
            "status": {
                "type": "string",
                "enum": ["skipped", "passed", "failed", "inconclusive"],
            },
            "primary_result_ref": {"type": "string"},
            "test_result_refs": {"type": "array", "items": {"type": "string"}},
            "validator_findings": {"type": "array", "items": {"type": "string"}},
            "decision_impact": {"type": "string"},
            "skip_reason": {"type": "string"},
        },
        "required": ["trigger", "scope", "mode", "status"],
    },
}

CONTROL_PLANE_SNAPSHOT_SCHEMA = {
    "name": "control_plane_snapshot",
    "description": (
        "Write a local Vesta control-plane snapshot from run artifacts so "
        "CLI/TUI/ACP/dashboard surfaces can display state without becoming "
        "the source of truth."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "next_action": {
                "type": "string",
                "description": "Optional operator-facing next action override.",
            },
        },
    },
}

HANDOFF_GENERATE_SCHEMA = {
    "name": "handoff_generate",
    "description": (
        "Generate a fresh-context Vesta handoff from run files, including "
        "objective, decisions, claims, gaps, artifacts, worker state, "
        "verification/finalization, residual risk, and exactly one next action."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "objective": {"type": "string"},
            "completed_work": {"type": "array", "items": {"type": "string"}},
            "next_action": {"type": "string"},
        },
    },
}

RESEARCH_ARTIFACT_SECTION_WRITE_SCHEMA = {
    "name": "research_artifact_section_write",
    "description": (
        "Append one bounded section to a Vesta evidence artifact and record it "
        "in the artifact manifest. Use instead of one large markdown write_file "
        "payload for evidence-heavy outputs."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Evidence artifact path to create or append.",
            },
            "section": {
                "type": "string",
                "enum": ["sources", "paper_coverage", "claims_verdict", "gaps"],
                "description": "Report section being appended.",
            },
            "content": {
                "type": "string",
                "description": "Bounded markdown content for this section only.",
            },
        },
        "required": ["path", "section", "content"],
    },
}


def _handle_ledger_append(args, **kw) -> str:
    try:
        result = append_ledger_entry(
            entry_type=args.get("entry_type", ""),
            title=args.get("title", ""),
            statement=args.get("statement", ""),
            refs=args.get("refs") or [],
            status=args.get("status", "active"),
            materiality=args.get("materiality", "medium"),
            next_action=args.get("next_action") or None,
            structured_payload=args.get("structured_payload") or None,
            session_id=os.getenv("HERMES_SESSION_ID", ""),
            actor="agent",
        )
        _note_runtime_progress("ledger_append")
        return json.dumps({"success": True, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


def _bounded_limit(args, default: int) -> int:
    try:
        value = int(args.get("limit", default))
    except (TypeError, ValueError):
        return default
    return max(1, min(value, 50))


def _handle_ledger_status(args, **kw) -> str:
    try:
        result = ledger_status(
            limit=_bounded_limit(args, 8),
            session_id=os.getenv("HERMES_SESSION_ID", ""),
        )
        return json.dumps({"success": True, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


def _handle_ledger_tail(args, **kw) -> str:
    try:
        result = ledger_tail(
            limit=_bounded_limit(args, 10),
            entry_types=args.get("entry_types") or None,
            session_id=os.getenv("HERMES_SESSION_ID", ""),
        )
        return json.dumps({"success": True, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


def _handle_ledger_search(args, **kw) -> str:
    try:
        result = ledger_search(
            query=args.get("query", ""),
            limit=_bounded_limit(args, 10),
            entry_types=args.get("entry_types") or None,
            session_id=os.getenv("HERMES_SESSION_ID", ""),
        )
        return json.dumps({"success": True, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


def _handle_artifact_manifest_status(args, **kw) -> str:
    try:
        result = artifact_manifest_status(session_id=os.getenv("HERMES_SESSION_ID", ""))
        return json.dumps({"success": True, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


def _handle_run_status(args, **kw) -> str:
    try:
        result = run_status(session_id=os.getenv("HERMES_SESSION_ID", ""))
        return json.dumps({"success": True, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


def _handle_whole_document_read(args, **kw) -> str:
    try:
        result = process_document(
            path=args.get("path", ""),
            objective=args.get("objective", ""),
            session_id=os.getenv("HERMES_SESSION_ID", ""),
        )
        return json.dumps({"success": True, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


def _handle_artifact_record(args, **kw) -> str:
    try:
        result = record_artifact(
            path=args.get("path", ""),
            artifact_type=args.get("artifact_type", ""),
            expected_by=args.get("expected_by", ""),
            status=args.get("status", "expected"),
            impact_if_missing=args.get("impact_if_missing", ""),
            session_id=os.getenv("HERMES_SESSION_ID", ""),
        )
        _note_runtime_progress("artifact_record")
        return json.dumps({"success": True, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


def _handle_finalize_run(args, **kw) -> str:
    try:
        result = write_finalization(
            objective=args.get("objective", ""),
            verification=args.get("verification", ""),
            skip_reason=args.get("skip_reason", ""),
            unsupported_claims=args.get("unsupported_claims") or [],
            failures=args.get("failures") or [],
            contradictions=args.get("contradictions") or [],
            gaps=args.get("gaps") or [],
            next_action=args.get("next_action") or None,
            session_id=os.getenv("HERMES_SESSION_ID", ""),
        )
        _note_runtime_progress("finalize_run")
        return json.dumps({"success": True, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


def _handle_worker_state_record(args, **kw) -> str:
    try:
        result = record_worker_state(
            worker_id=args.get("worker_id", ""),
            objective=args.get("objective", ""),
            status=args.get("status", ""),
            model_lane=args.get("model_lane", ""),
            output_contract=args.get("output_contract") or None,
            child_session_id=args.get("child_session_id", ""),
            child_run_id=args.get("child_run_id", ""),
            expected_artifact_paths=args.get("expected_artifact_paths"),
            artifact_paths=args.get("artifact_paths"),
            failures=args.get("failures") or [],
            gaps=args.get("gaps") or [],
            material_claims=args.get("material_claims"),
            parent_acceptance=args.get("parent_acceptance", "unreviewed"),
            spot_audit=args.get("spot_audit", ""),
            next_action=args.get("next_action", ""),
            session_id=os.getenv("HERMES_SESSION_ID", ""),
        )
        _note_runtime_progress("worker_state_record")
        return json.dumps({"success": True, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


def _handle_coding_eval_start(args, **kw) -> str:
    try:
        result = start_coding_eval(
            original_workspace=args.get("original_workspace", ""),
            prompt=args.get("prompt", ""),
            model=args.get("model", ""),
            provider=args.get("provider", ""),
            config=args.get("config") or None,
            excluded_paths=args.get("excluded_paths") or [],
            include_sensitive_paths=bool(args.get("include_sensitive_paths", False)),
            session_id=os.getenv("HERMES_SESSION_ID", ""),
        )
        return json.dumps({"success": True, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


def _handle_coding_eval_capture(args, **kw) -> str:
    try:
        result = capture_coding_eval_result(
            eval_id=args.get("eval_id", ""),
            verification_command=args.get("verification_command", ""),
            verification_exit_status=int(args.get("verification_exit_status", 0)),
            verification_output=args.get("verification_output", ""),
            failure_reason=args.get("failure_reason", ""),
            skip_reason=args.get("skip_reason", ""),
            session_id=os.getenv("HERMES_SESSION_ID", ""),
        )
        return json.dumps({"success": True, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


def _handle_raw_ref_purge(args, **kw) -> str:
    try:
        result = purge_raw_ref(
            raw_ref=args.get("raw_ref", ""),
            reason=args.get("reason", ""),
            session_id=os.getenv("HERMES_SESSION_ID", ""),
        )
        return json.dumps({"success": True, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


def _handle_validator_result_record(args, **kw) -> str:
    try:
        result = record_validator_result(
            trigger=args.get("trigger", ""),
            scope=args.get("scope", ""),
            mode=args.get("mode", ""),
            status=args.get("status", ""),
            primary_result_ref=args.get("primary_result_ref", ""),
            test_result_refs=args.get("test_result_refs") or [],
            validator_findings=args.get("validator_findings") or [],
            decision_impact=args.get("decision_impact", ""),
            skip_reason=args.get("skip_reason", ""),
            session_id=os.getenv("HERMES_SESSION_ID", ""),
        )
        _note_runtime_progress("validator_result_record")
        return json.dumps({"success": True, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


def _handle_control_plane_snapshot(args, **kw) -> str:
    try:
        result = write_control_plane_snapshot(
            next_action=args.get("next_action", ""),
            session_id=os.getenv("HERMES_SESSION_ID", ""),
        )
        _note_runtime_progress("control_plane_snapshot")
        return json.dumps({"success": True, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


def _handle_handoff_generate(args, **kw) -> str:
    try:
        result = write_handoff(
            objective=args.get("objective", ""),
            completed_work=args.get("completed_work") or [],
            next_action=args.get("next_action", ""),
            session_id=os.getenv("HERMES_SESSION_ID", ""),
        )
        return json.dumps({"success": True, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


def _handle_research_artifact_section_write(args, **kw) -> str:
    if not isinstance(args, dict):
        args = {}
    missing = [
        key
        for key in ("path", "section", "content")
        if key not in args or (key != "content" and not args.get(key))
    ]
    if missing:
        return json.dumps(
            {
                "success": False,
                "code": "vesta_research_artifact_section_args_missing_or_corrupt",
                "error": (
                    "research_artifact_section_write missing required field(s): "
                    + ", ".join(missing)
                ),
                "repair_hint": (
                    "Retry with one bounded evidence artifact section: path, section "
                    "(sources, paper_coverage, claims_verdict, or gaps), and compact "
                    "content. Do not fall back to one large write_file payload."
                ),
            },
            ensure_ascii=False,
        )
    try:
        result = write_research_artifact_section(
            path=args.get("path", ""),
            section=args.get("section", ""),
            content=args.get("content", ""),
            session_id=os.getenv("HERMES_SESSION_ID", ""),
        )
        _note_runtime_progress("research_artifact_section_write")
        return json.dumps({"success": True, **result}, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


registry.register(
    name="ledger_append",
    toolset="vesta",
    schema=LEDGER_APPEND_SCHEMA,
    handler=_handle_ledger_append,
    emoji="📒",
    max_result_size_chars=20_000,
)

registry.register(
    name="ledger_status",
    toolset="vesta",
    schema=LEDGER_STATUS_SCHEMA,
    handler=_handle_ledger_status,
    emoji="📒",
    max_result_size_chars=20_000,
)

registry.register(
    name="ledger_tail",
    toolset="vesta",
    schema=LEDGER_TAIL_SCHEMA,
    handler=_handle_ledger_tail,
    emoji="📒",
    max_result_size_chars=20_000,
)

registry.register(
    name="ledger_search",
    toolset="vesta",
    schema=LEDGER_SEARCH_SCHEMA,
    handler=_handle_ledger_search,
    emoji="🔎",
    max_result_size_chars=20_000,
)

registry.register(
    name="artifact_manifest_status",
    toolset="vesta",
    schema=ARTIFACT_MANIFEST_STATUS_SCHEMA,
    handler=_handle_artifact_manifest_status,
    emoji="📦",
    max_result_size_chars=20_000,
)

registry.register(
    name="run_status",
    toolset="vesta",
    schema=RUN_STATUS_SCHEMA,
    handler=_handle_run_status,
    emoji="🧭",
    max_result_size_chars=30_000,
)

registry.register(
    name="artifact_record",
    toolset="vesta",
    schema=ARTIFACT_RECORD_SCHEMA,
    handler=_handle_artifact_record,
    emoji="📦",
    max_result_size_chars=20_000,
)

registry.register(
    name="finalize_run",
    toolset="vesta",
    schema=FINALIZE_RUN_SCHEMA,
    handler=_handle_finalize_run,
    emoji="✅",
    max_result_size_chars=20_000,
)

registry.register(
    name="worker_state_record",
    toolset="vesta",
    schema=WORKER_STATE_RECORD_SCHEMA,
    handler=_handle_worker_state_record,
    emoji="🧭",
    max_result_size_chars=20_000,
)

registry.register(
    name="coding_eval_start",
    toolset="vesta",
    schema=CODING_EVAL_START_SCHEMA,
    handler=_handle_coding_eval_start,
    emoji="🧪",
    max_result_size_chars=20_000,
)

registry.register(
    name="coding_eval_capture",
    toolset="vesta",
    schema=CODING_EVAL_CAPTURE_SCHEMA,
    handler=_handle_coding_eval_capture,
    emoji="🧾",
    max_result_size_chars=20_000,
)

registry.register(
    name="raw_ref_purge",
    toolset="vesta",
    schema=RAW_REF_PURGE_SCHEMA,
    handler=_handle_raw_ref_purge,
    emoji="🧹",
    max_result_size_chars=20_000,
)

registry.register(
    name="validator_result_record",
    toolset="vesta",
    schema=VALIDATOR_RESULT_RECORD_SCHEMA,
    handler=_handle_validator_result_record,
    emoji="🔎",
    max_result_size_chars=20_000,
)

registry.register(
    name="control_plane_snapshot",
    toolset="vesta",
    schema=CONTROL_PLANE_SNAPSHOT_SCHEMA,
    handler=_handle_control_plane_snapshot,
    emoji="🖥️",
    max_result_size_chars=20_000,
)

registry.register(
    name="handoff_generate",
    toolset="vesta",
    schema=HANDOFF_GENERATE_SCHEMA,
    handler=_handle_handoff_generate,
    emoji="🧷",
    max_result_size_chars=20_000,
)

registry.register(
    name="research_artifact_section_write",
    toolset="vesta",
    schema=RESEARCH_ARTIFACT_SECTION_WRITE_SCHEMA,
    handler=_handle_research_artifact_section_write,
    emoji="🧾",
    max_result_size_chars=20_000,
)

registry.register(
    name="whole_document_read",
    toolset="vesta",
    schema=WHOLE_DOCUMENT_READ_SCHEMA,
    handler=_handle_whole_document_read,
    emoji="📚",
    max_result_size_chars=100_000,
)
