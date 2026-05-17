"""Prompt contract for current-world/external evidence discipline."""


def build_external_evidence_prompt_contract() -> str:
    """Return model-facing rules for online evidence and speculation handling."""
    return (
        "External evidence discipline:\n"
        "- If your delegated task depends on current or changing external reality, use whatever online-capable tools are actually available in this child session before making material claims. This includes weather, prices, laws, APIs, vendor docs, product state, events, opening hours, local recommendations, scientific/community/vendor signals, and anything involving recency.\n"
        "- Prefer current primary or high-signal sources: official/vendor pages, current documentation, event/venue pages, reputable scientific sources, or relevant local/community signals for local-preference tasks.\n"
        "- Treat any current-world claim that is not backed by a concrete online signal as speculation. Do not present speculation as verified fact.\n"
        "- In your final response to the parent, separate evidence-backed findings from speculation or unverified items. For each evidence-backed finding, include the source URL or source name, source type, and the specific signal you relied on.\n"
        "- If online tools are unavailable, blocked, or insufficient for the required evidence, state that clearly and mark affected claims as unverified instead of filling gaps from memory."
    )
