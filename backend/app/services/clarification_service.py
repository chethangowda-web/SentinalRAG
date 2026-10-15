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


def detect_ambiguity(question: str, chunks: list[dict]) -> str | None:
    if _vague_word_re.search(question):
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

    prompt = (
        "Analyze if the following question is ambiguous given the context.\n"
        "If ambiguous, suggest a clarification question. "
        "If clear, output 'CLEAR'.\n\n"
        f"Question: {question}\n\n"
        f"Context: {context}\n\n"
        "Output (either 'CLEAR' or a clarification question):"
    )

    try:
        response = invoke_with_retry(llm, prompt)
        result = response.content.strip()
        elapsed = round((time.perf_counter() - start) * 1000, 1)
        if result.upper() == "CLEAR":
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
