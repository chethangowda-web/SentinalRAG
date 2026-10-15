import logging
import re

from app.services.llm import build_llm, invoke_with_retry

logger = logging.getLogger(__name__)


_NUMBER_RE = re.compile(r"\b\d+[\.,]?\d*\b")


_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = build_llm(max_tokens=16, timeout=20, temperature=0.0)
    return _llm


def verify_contradiction(question: str, chunks: list[dict], reason: str | None) -> bool | None:
    """Ask the LLM whether flagged passages really give conflicting answers to the question.

    Returns True/False, or None when it cannot be decided (no LLM, an error, or an unclear reply).
    """
    llm = _get_llm()
    if llm is None:
        return None

    passages = "\n\n".join(
        f"[{i + 1}] {(c.get('text') or '')[:600]}" for i, c in enumerate(chunks[:6]) if c.get("text")
    )
    prompt = (
        "The passages below were flagged by a rough keyword check as possibly contradicting each other. "
        "Decide whether they actually give CONFLICTING answers to the question. "
        "Different plans, tiers, products, dates or scopes are NOT a conflict, and neither is a number "
        "that merely appears in unrelated sentences.\n\n"
        f"Question: {question}\n\nPassages:\n{passages}\n\n"
        "Reply with exactly one word: YES (they conflict) or NO."
    )
    try:
        reply = (invoke_with_retry(llm, prompt).content or "").strip().upper()
    except Exception as exc:
        logger.warning("Contradiction verification failed, keeping the keyword result: %s", str(exc)[:160])
        return None
    if reply.startswith("YES"):
        return True
    if reply.startswith("NO"):
        return False
    return None


def detect_contradictions(chunks: list[dict], question: str | None = None) -> tuple[bool, str | None]:
    """Keyword screen for conflicting sources; when a question is given, an LLM confirms any hit.

    The keyword check alone fires on almost any pair of chunks containing numbers, so a hit is
    only trusted outright when it cannot be verified.
    """
    if len(chunks) < 2:
        return False, None

    texts = [c.get("text", "") for c in chunks if c.get("text")]

    reason = _check_number_conflicts(texts) or _check_policy_conflicts(texts)
    if not reason:
        return False, None

    if question and verify_contradiction(question, chunks, reason) is False:
        logger.info("Keyword contradiction rejected by LLM verification: %s", reason[:80])
        return False, None

    return True, reason


_CONFLICT_PHRASES = [
    (r"(?:refund|return|policy|period|limit|maximum|minimum|duration|deadline|fee|cost|price|rate)",
     "policy term"),
]


def _check_number_conflicts(texts: list[str]) -> str | None:
    number_map: dict[str, list[str]] = {}
    for text in texts:
        for match in _NUMBER_RE.finditer(text):
            num = match.group()
            context_start = max(0, match.start() - 50)
            context_end = min(len(text), match.end() + 50)
            context = text[context_start:context_end].strip()
            key = f"number:{num}"
            if key not in number_map:
                number_map[key] = []
            number_map[key].append(context)

    for num, contexts in number_map.items():
        unique_contexts = set(c.lower() for c in contexts)
        if len(unique_contexts) > 1:
            return (
                f"Conflicting numbers found: value {num} appears in "
                f"different contexts across chunks (e.g., "
                f"'{contexts[0][:80]}...' vs '{contexts[1][:80]}...')"
            )

    number_contexts: list[tuple[str, str, str]] = []
    for i, text in enumerate(texts):
        for match in _NUMBER_RE.finditer(text):
            num = match.group()
            ctx_start = max(0, match.start() - 50)
            ctx_end = min(len(text), match.end() + 50)
            ctx = text[ctx_start:ctx_end].lower()
            tag = _tag_context(ctx)
            if tag:
                number_contexts.append((num, tag, ctx))

    for i, (num1, tag1, ctx1) in enumerate(number_contexts):
        for num2, tag2, ctx2 in number_contexts[i+1:]:
            if num1 != num2 and tag1 == tag2:
                return (
                    f"Conflicting values for '{tag1}': '{num1}' vs '{num2}' "
                    f"(e.g., '{ctx1[:80]}...' vs '{ctx2[:80]}...')"
                )

    return None


def _tag_context(context: str) -> str | None:
    for pattern, label in _CONFLICT_PHRASES:
        if re.search(pattern, context, re.IGNORECASE):
            return label
    return None


def _check_policy_conflicts(texts: list[str]) -> str | None:
    policy_indicators = [
        (r"(?:no\s+)?refund", "Refund policy"),
        (r"(?:not\s+)?allowed", "Permissions"),
        (r"(?:not\s+)?required", "Requirements"),
        (r"effective\s+date|valid\s+from|expir", "Dates"),
        (r"interest\s+rate|annual\s+percentage|apr", "Rates"),
    ]

    for pattern, label in policy_indicators:
        matches = [(i, re.findall(pattern, t, re.IGNORECASE)) for i, t in enumerate(texts)]
        matches = [(i, m) for i, m in matches if m]
        if len(matches) > 1:
            positive = any(not re.search(r"(?:no |not |excluding )", m[0].lower()) if m else False for _, m in matches)
            negative = any(re.search(r"(?:no |not |excluding )", m[0].lower()) if m else False for _, m in matches)
            if positive and negative:
                reasons = [f"Chunk {i}: '{m[0][:80]}...'" for i, m in matches]
                return f"Conflicting policy detected ({label}): {' vs '.join(reasons)}"

    return None
