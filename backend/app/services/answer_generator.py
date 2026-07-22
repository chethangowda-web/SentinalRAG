import logging
import time
import traceback

from app.core.config import settings
from app.services.token_counter import count_tokens

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
            temperature=0.05,
            max_tokens=256,
            timeout=30,
            max_retries=1,
        )
    return _llm


def generate_answer(question: str, chunks: list[dict]) -> str:
    llm = _get_llm()
    if llm is None:
        logger.warning("No LLM configured, returning chunk-based fallback")
        return _no_llm_fallback(question, chunks, "no_llm")

    start = time.perf_counter()

    context_parts = []
    for i, chunk in enumerate(chunks[:5]):
        doc_id = chunk.get("document_id", "?")
        text = (chunk.get("text", "") or "")[:2000]
        context_parts.append(f"[Source {i+1}] (Document: {doc_id})\n{text}")

    context = "\n\n".join(context_parts)

    prompt = (
        "You are a precise RAG answer generator. Answer the question "
        "using ONLY the provided context.\n\n"
        "Rules:\n"
        "- If the context does not contain enough information, say "
        "'I don't have enough information to answer this question.'\n"
        "- Never invent information or hallucinate\n"
        "- Cite sources using [Source N] markers\n"
        "- Be concise and direct\n"
        "- If there are contradictions in the context, mention them\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )

    try:
        response = llm.invoke(prompt)
        answer = response.content.strip()
        elapsed = round((time.perf_counter() - start) * 1000, 1)
        logger.info("Answer generated in %.1fms from %d chunks", elapsed, len(chunks))
        return answer
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
    if reason == "rate_limit":
        notice = (
            "\n\n> **LLM rate limit reached.** Generated content below is raw retrieved text. "
            "Add a valid API key to your `.env` for unlimited usage."
        )
    elif reason == "no_llm":
        notice = (
            "\n\n> **No LLM configured.** Set `DEEPSEEK_API_KEY` or `FEATHERLESS_API_KEY` "
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
