import logging
import re

from app.services.llm import build_llm, invoke_with_retry

logger = logging.getLogger(__name__)

# Questions longer than this are assumed to stand on their own
MAX_FOLLOWUP_WORDS = 12
HISTORY_MESSAGES = 6

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = build_llm(max_tokens=128, timeout=30, temperature=0.0)
    return _llm


def standalone_question(question: str, history: list[tuple[str, str]]) -> str | None:
    """Rewrite a follow-up ("And are there any exceptions?") into a question that makes sense alone.

    `history` is the earlier (role, text) turns, oldest first. Returns None when there is nothing to
    resolve or the rewrite fails, in which case the caller keeps the original question.
    """
    if not history or len(question.split()) > MAX_FOLLOWUP_WORDS:
        return None
    llm = _get_llm()
    if llm is None:
        return None

    transcript = "\n".join(f"{role}: {text[:300]}" for role, text in history[-HISTORY_MESSAGES:])
    prompt = (
        "Rewrite the user's last question so it can be understood without the conversation. "
        "Replace references like 'it', 'that', 'and the exceptions?' with what they refer to. "
        "If the question already stands on its own, output it unchanged. "
        "Output only the question, nothing else.\n\n"
        f"Conversation:\n{transcript}\n\nLast question: {question}\n\nStandalone question:"
    )
    try:
        rewritten = invoke_with_retry(llm, prompt).content.strip().strip('"')
    except Exception as e:
        logger.warning("Follow-up rewrite failed, using the original question: %s", e)
        return None
    rewritten = re.sub(r"^(standalone question:)\s*", "", rewritten, flags=re.IGNORECASE)
    if not rewritten or len(rewritten) > 400 or "\n" in rewritten:
        return None
    return rewritten
