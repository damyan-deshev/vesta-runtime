"""Vesta runtime substrate.

Vesta is layered on top of Hermes sessions. Hermes keeps transcript/session
history; Vesta keeps durable run state that models and humans can inspect.
"""

from .state import (
    VestaRun,
    append_ledger_entry,
    artifact_manifest_status,
    capture_raw_output,
    create_run,
    get_current_run,
    guard_run_end,
    ledger_search,
    ledger_status,
    ledger_tail,
    purge_raw_ref,
    record_session_rotation,
    record_artifact,
    record_worker_state,
    record_validator_result,
    set_current_run,
    run_status,
    write_control_plane_snapshot,
    write_research_artifact_section,
    write_resume_packet,
    write_handoff,
    write_finalization,
)
from .whole_document import process_document
from .coding_eval import capture_coding_eval_result, start_coding_eval
from .eval_contract import (
    background_review_allowed_for_eval,
    enforce_eval_contract,
    eval_mode_enabled,
    seed_eval_contract_from_prompt,
    validate_delegate_task_against_eval_contract,
)
from .closure import build_closure_prompt_contract

__all__ = [
    "VestaRun",
    "append_ledger_entry",
    "artifact_manifest_status",
    "capture_raw_output",
    "create_run",
    "get_current_run",
    "guard_run_end",
    "ledger_search",
    "ledger_status",
    "ledger_tail",
    "purge_raw_ref",
    "record_session_rotation",
    "record_artifact",
    "record_worker_state",
    "record_validator_result",
    "set_current_run",
    "run_status",
    "write_control_plane_snapshot",
    "write_research_artifact_section",
    "write_resume_packet",
    "write_handoff",
    "write_finalization",
    "process_document",
    "start_coding_eval",
    "capture_coding_eval_result",
    "background_review_allowed_for_eval",
    "enforce_eval_contract",
    "eval_mode_enabled",
    "seed_eval_contract_from_prompt",
    "validate_delegate_task_against_eval_contract",
    "build_closure_prompt_contract",
]
