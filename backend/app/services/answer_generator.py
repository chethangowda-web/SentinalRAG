import hashlib
import logging
import threading
import time
import traceback
from collections import OrderedDict

from app.core.config import settings
from app.services.llm import LLMQuotaExhausted, build_llm, invoke_with_retry, stream_with_retry
from app.services.token_counter import count_tokens

logger = logging.getLogger(__name__)

_llm = None

# Identical question + identical retrieved passages give an identical answer, so remember it:
# repeat questions, retries and benchmark reruns then cost no LLM request.
_answer_cache: "OrderedDict[str, str]" = OrderedDict()
_cache_lock = threading.Lock()


def _cache_key(question: str, chunks: list[dict]) -> str:
    ids = "|".join(str(c.get("chunk_id") or c.get("text", "")[:80]) for c in chunks[:8])
    return hashlib.sha256(f"{question.strip().lower()}||{ids}".encode()).hexdigest()


def _cache_get(key: str) -> str | None:
    with _cache_lock:
        answer = _answer_cache.get(key)
        if answer is not None:
            _answer_cache.move_to_end(key)
        return answer


def _cache_put(key: str, answer: str) -> None:
    if settings.ANSWER_CACHE_SIZE <= 0:
        return
    with _cache_lock:
        _answer_cache[key] = answer
        _answer_cache.move_to_end(key)
        while len(_answer_cache) > settings.ANSWER_CACHE_SIZE:
            _answer_cache.popitem(last=False)


def clear_answer_cache() -> None:
    with _cache_lock:
        _answer_cache.clear()


def _get_llm():
    global _llm
    if _llm is None:
        _llm = build_llm(max_tokens=settings.LLM_MAX_TOKENS, timeout=60, temperature=0.05)
    return _llm


def generate_answer(question: str, chunks: list[dict], on_token=None) -> str:
    """Answer from the passages. When `on_token` is given the text is also passed to it piece by piece."""
    if not chunks:
        logger.info("No chunks to answer from")
        return (
            "No relevant information was found in the uploaded documents."
        )

    llm = _get_llm()
    if llm is None:
        logger.warning("No LLM configured, returning chunk-based fallback")
        return _no_llm_fallback(question, chunks, "no_llm")

    cache_key = _cache_key(question, chunks)
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.info("Answer served from cache")
        if on_token:
            on_token(cached)
        return cached

    start = time.perf_counter()

    context_parts = []
    for i, chunk in enumerate(chunks[:8]):
        doc_id = chunk.get("document_id", "?")
        text = (chunk.get("text", "") or "")[:2000]
        context_parts.append(f"[Source {i+1}] (Document: {doc_id})\n{text}")

    context = "\n\n".join(context_parts)

    prompt = (
        "You are a precise RAG answer generator. Answer the question "
        "using ONLY the provided context below.\n\n"
        "STRICT RULES:\n"
        "1. Answer ONLY from the provided context. Never use your own knowledge.\n"
        "2. If the context does not contain enough information to answer, "
        "say exactly: 'I don't have enough information to answer this question.'\n"
        "3. Never invent, guess, or hallucinate any information.\n"
        "4. Cite sources using [Source N] markers for every factual claim.\n"
        "5. Be concise and direct. Do not add introductory phrases.\n"
        "6. If different sources provide conflicting information, mention the contradiction.\n"
        "7. If the question has nothing to do with the provided context, "
        "say 'I don't have enough information to answer this question.'\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )

    try:
        if on_token and hasattr(llm, "stream"):
            answer = stream_with_retry(llm, prompt, on_token, rate_limit_retries=2).strip()
        else:
            answer = invoke_with_retry(llm, prompt, rate_limit_retries=2).content.strip()
        elapsed = round((time.perf_counter() - start) * 1000, 1)
        logger.info("Answer generated in %.1fms from %d chunks", elapsed, len(chunks))
        if answer:
            _cache_put(cache_key, answer)
        return answer
    except LLMQuotaExhausted as e:
        logger.error("LLM quota exhausted: %s", e)
        return _no_llm_fallback(question, chunks, "quota", str(int(e.retry_after_seconds)))
    except Exception as e:
        err_str = str(e)
        logger.error("LLM generation failed: %s", err_str[:200])
        logger.debug("LLM failure traceback:\n%s", traceback.format_exc())
        reason = "rate_limit" if "429" in err_str or "rate_limit" in err_str.lower() else "llm_error"
        return _no_llm_fallback(question, chunks, reason, err_str[:300])


def get_usage_tokens(question: str, chunks: list[dict], answer: str) -> dict:
    prompt_text = (
        f"Question: {question}\n"
        + "\n".join(c.get("text", "") or "" for c in chunks)
    )
    prompt_tokens = count_tokens(prompt_text)
    completion_tokens = count_tokens(answer)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


def _no_llm_fallback(question: str, chunks: list[dict], reason: str = "unknown", detail: str = "") -> str:
    if not chunks:
        return (
            "I don't have enough information to answer this question. "
            "Please upload relevant documents or rephrase your question."
        )

    top = chunks[0]
    snippet = top.get("text", "")[:300]
    doc_id = top.get("document_id", "unknown")

    notice = ""
    if reason == "quota":
        hours = max(1, round(int(detail or 0) / 3600)) if detail.isdigit() else 1
        notice = (
            "\n\n> **The AI service's request quota is used up for now** (it resets in about "
            f"{hours} hour(s)). Showing the most relevant retrieved passage instead of a written answer."
        )
    elif reason == "rate_limit":
        notice = (
            "\n\n> **LLM rate limit reached.** Generated content below is raw retrieved text. "
            "Add a valid API key to your `.env` for unlimited usage."
        )
    elif reason == "no_llm":
        notice = (
            "\n\n> **No LLM configured.** Set `GEMINI_API_KEY` (or `DEEPSEEK_API_KEY`) "
            "in your `.env` file to enable AI-powered answers."
        )
    elif reason == "llm_error":
        notice = (
            f"\n\n> **LLM error:** {detail[:200]}\n"
            "Displaying raw retrieved content below."
        )

    return (
        f"Based on the retrieved documents (source: {doc_id}):\n\n"
        f"{snippet}\n\n"
        f"_(LLM is unavailable. Displaying the most relevant retrieved content above.)_"
        f"{notice}"
    )
