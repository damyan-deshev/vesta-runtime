"""Vesta closure-discipline prompt contract."""

from __future__ import annotations


def build_closure_prompt_contract() -> str:
    """Return the stable prompt block for Vesta closure discipline."""

    return (
        "Vesta closure discipline:\n"
        "- After material actions, update durable Vesta state when state tools are available.\n"
        "- Use run_status/ledger_status/artifact_manifest_status to inspect Vesta state; "
        "use ledger_append/artifact_record/worker_state_record/validator_result_record "
        "to record it. Do not inspect tool source or simulate state via terminal when "
        "typed Vesta tools can do the job.\n"
        "- For long or sectioned research artifacts, prefer research_artifact_section_write "
        "with bounded sections over one large write_file payload.\n"
        "- Before finalizing, run the cheapest relevant verification for the domain: "
        "artifact existence/freshness/required content; source refs, contradictions, "
        "and gaps for research; decision and next-action consistency for planning; "
        "parent acceptance or spot audit for workers; syntax/import/compile or focused "
        "tests when code changed.\n"
        "- If verification fails, fix forward and rerun the same relevant check; "
        "if unavailable, record a clear skip_reason.\n"
        "- Close with finalize_run after required artifacts/state are recorded. Final "
        "answers must match Vesta state; do not claim completion while "
        "verification, skip reason, artifacts, or worker acceptance are missing."
    )
