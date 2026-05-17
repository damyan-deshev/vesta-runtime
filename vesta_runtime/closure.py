"""Vesta closure-discipline prompt contract."""

from __future__ import annotations


def build_closure_prompt_contract() -> str:
    """Return the stable prompt block for Vesta closure discipline."""

    return (
        "Vesta closure discipline:\n"
        "- After material actions, update durable Vesta state when state tools are available.\n"
        "- Before finalizing, run the cheapest relevant verification for the domain: "
        "artifact existence/freshness/required content; source refs, contradictions, "
        "and gaps for research; decision and next-action consistency for planning; "
        "parent acceptance or spot audit for workers; syntax/import/compile or focused "
        "tests when code changed.\n"
        "- If verification fails, fix forward and rerun the same relevant check.\n"
        "- If verification is inappropriate or unavailable, record a clear skip_reason.\n"
        "- Final answers must match Vesta state; do not claim completion while "
        "verification, skip reason, artifacts, or worker acceptance are missing."
    )
