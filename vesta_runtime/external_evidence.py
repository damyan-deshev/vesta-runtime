"""Prompt contract for current-world/external evidence discipline."""


def build_external_evidence_prompt_contract() -> str:
    """Return model-facing rules for online evidence and speculation handling."""
    return (
        "External evidence discipline:\n"
        "- If your delegated task depends on current or changing external reality, use whatever online-capable tools are actually available in this child session before making material claims. This includes weather, prices, laws, APIs, vendor docs, product state, events, opening hours, local recommendations, scientific/community/vendor signals, and anything involving recency.\n"
        "- Prefer current primary or high-signal sources: official/vendor pages, current documentation, event/venue pages, reputable scientific sources, or relevant local/community signals for local-preference tasks.\n"
        "- Use the shortest evidence path that can answer the task: start with the most direct source or search result, fetch bounded snippets or compact outputs, and avoid dumping full pages, raw HTML, logs, or large terminal output unless complete coverage is truly required.\n"
        "- Web evidence/extraction results are normalized text or markdown evidence, not raw HTML, JavaScript, DOM nodes, or live browser objects. Do not repeat retrieval waiting for DOM-like output; use browser tools only when you specifically need interaction, rendered page state, element refs, visual checks, or JavaScript behavior.\n"
        "- Hard per-call output budget, not a task budget: shape terminal/browser retrieval before calling the tool so one call returns a compact normalized text excerpt, ideally under about 12000 characters. Prefer markdown/text extraction, field selection, head/sed windows, or targeted follow-up calls over broad raw dumps. If more coverage is needed, checkpoint concise findings/gaps and continue with a targeted next window or ask the parent for another iteration.\n"
        "- For long files, pages, API payloads, or search results, follow locate-then-bounded-read discipline: find a promising signal first, inspect a small nearby window, then expand only if that window does not answer the question.\n"
        "- If the same tool, URL, query, or source fails twice or starts looping, stop that path. Switch to a different source/tool or report an evidence/capability gap instead of repeating the failure.\n"
        "- Once you have enough evidence for a bounded answer, answer with citations and gaps. Do not spend the full iteration or time budget trying to over-perfect low-value details.\n"
        "- Treat any current-world claim that is not backed by a concrete online signal as speculation. Do not present speculation as verified fact.\n"
        "- In your final response to the parent, separate evidence-backed findings from speculation or unverified items. For each evidence-backed finding, include the source URL or source name, source type, and the specific signal you relied on.\n"
        "- If online tools are unavailable, blocked, or insufficient for the required evidence, state that clearly and mark affected claims as unverified instead of filling gaps from memory."
    )
