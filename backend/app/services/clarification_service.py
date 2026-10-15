import logging
import re
import time

from app.services.llm import build_llm, invoke_with_retry

logger = logging.getLogger(__name__)


_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = build_llm(max_tokens=256, timeout=30, temperature=0.1)
    return _llm


_vague_word_re = re.compile(
    r"\b(?:it|this|that|they|them|those|these|there|something|"
    r"someone|somebody|thing|stuff|what about|how about|"
    r"what is the fee|what is the cost|what is the price|"
    r"what are the terms|what are the conditions|"
    r"tell me about|explain)\b",
    re.IGNORECASE,
)


def detect_ambiguity(
    question: str, chunks: list[dict], use_keywords: bool = True, titles: list[str] | None = None
) -> str | None:
    """Return a clarifying question if the question is too vague to answer, else None.

    The keyword screen is quick but crude (it matches words like "explain" and "that" in perfectly
    specific questions), so callers that run on every question pass use_keywords=False and rely on the LLM.
    """
    if use_keywords and _vague_word_re.search(question):
        if chunks:
            topics = _extract_topics(chunks)
            if topics:
                return (
                    f"I found several possible topics in the documents "
                    f"that might relate to your question: {topics}. "
                    f"Could you please be more specific?"
                )
        return (
            "Your question is a bit vague. "
            "Could you please provide more details or specify "
            "what exactly you're looking for?"
        )

    llm = _get_llm()
    if llm is None:
        return None

    start = time.perf_counter()

    context = "\n".join(
        c.get("text", "")[:200] for c in chunks[:3] if c.get("text")
    )

    titles_line = ""
    if titles:
        titles_line = (
            f"The user has these documents: {', '.join(titles)}. A question about a topic that matches "
            "one of these document names is CLEAR.\n"
        )

    prompt = (
        "Decide whether the following question is too vague to answer from documents. "
        "Be conservative: only call a question ambiguous if you cannot tell WHAT it is asking about. "
        "A question that names its subject (a policy, event, number, process or plan) is CLEAR, even if short "
        "or if the document might cover several plans or services; do not ask which one.\n"
        "CLEAR examples: 'What is the notice period for contract termination?', 'Who approves travel expenses?', "
        "'When do invoices get issued?'.\n"
        "AMBIGUOUS examples: 'What's the deadline?', 'Can you explain the process?', 'Tell me about the policy'.\n"
        f"{titles_line}"
        "If ambiguous, write one short clarifying question. If clear, output exactly CLEAR.\n\n"
        f"Question: {question}\n\n"
        f"Context: {context}\n\n"
        "Output (either 'CLEAR' or a clarification question):"
    )

    try:
        response = invoke_with_retry(llm, prompt)
        result = response.content.strip()
        elapsed = round((time.perf_counter() - start) * 1000, 1)
        if result.upper().startswith("CLEAR"):
            logger.info("Clarification check: clear (%.1fms)", elapsed)
            return None
        logger.info("Clarification needed: %s (%.1fms)", result[:80], elapsed)
        return result
    except Exception as e:
        logger.error("Clarification check failed: %s", e)
        return None


def _extract_topics(chunks: list[dict]) -> str:
    sections = set()
    for c in chunks:
        section = c.get("section")
        if section:
            sections.add(section)
        filename = c.get("filename")
        if filename:
            sections.add(f"in '{filename}'")

    if sections:
        return ", ".join(sorted(sections)[:5])
    return "various related topics"
