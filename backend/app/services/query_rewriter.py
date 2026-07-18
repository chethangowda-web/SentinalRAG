import logging
import time

from app.core.config import settings

logger = logging.getLogger(__name__)


_llm = None


def _get_llm():
    global _llm
    if _llm is None and settings.effective_llm_api_key:
        from langchain_openai import ChatOpenAI

        _llm = ChatOpenAI(
            model=settings.effective_llm_model,
            api_key=settings.effective_llm_api_key,
            base_url=settings.effective_llm_base_url,
            temperature=settings.LLM_TEMPERATURE,
        )
    return _llm


def rewrite_query(question: str) -> str:
    llm = _get_llm()
    if llm is None:
        logger.warning("No LLM configured, returning original question")
        return question

    start = time.perf_counter()

    prompt = (
        "You are a query rewriting assistant for a RAG system. "
        "Rewrite the following user question to be more specific, "
        "self-contained, and precise for document retrieval.\n\n"
        "Rules:\n"
        "- Expand vague pronouns (e.g., 'it' -> 'the refund policy')\n"
        "- Fix grammar\n"
        "- Preserve the original intent\n"
        "- Add relevant context from the question itself\n"
        "- Keep it concise (1-2 sentences)\n"
        "- Output ONLY the rewritten query, no explanation\n\n"
        f"Original question: {question}\n\n"
        "Rewritten query:"
    )

    try:
        response = llm.invoke(prompt)
        rewritten = response.content.strip()
        elapsed = round((time.perf_counter() - start) * 1000, 1)
        logger.info(
            "Query rewritten in %.1fms: '%s' -> '%s'",
            elapsed, question[:60], rewritten[:120],
        )
        return rewritten
    except Exception as e:
        logger.error("Query rewriting failed: %s", e)
        return question
