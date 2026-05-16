"""Vesta runtime substrate.

Vesta is layered on top of Hermes sessions. Hermes keeps transcript/session
history; Vesta keeps durable run state that models and humans can inspect.
"""

from .state import (
    VestaRun,
    append_ledger_entry,
    capture_raw_output,
    create_run,
    get_current_run,
    purge_raw_ref,
    record_session_rotation,
    record_artifact,
    record_worker_state,
    record_validator_result,
    set_current_run,
    write_control_plane_snapshot,
    write_resume_packet,
    write_handoff,
    write_finalization,
)
from .whole_document import process_document
from .coding_eval import capture_coding_eval_result, start_coding_eval

__all__ = [
    "VestaRun",
    "append_ledger_entry",
    "capture_raw_output",
    "create_run",
    "get_current_run",
    "purge_raw_ref",
    "record_session_rotation",
    "record_artifact",
    "record_worker_state",
    "record_validator_result",
    "set_current_run",
    "write_control_plane_snapshot",
    "write_resume_packet",
    "write_handoff",
    "write_finalization",
    "process_document",
    "start_coding_eval",
    "capture_coding_eval_result",
]
