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
        )
    return _llm


def generate_answer(question: str, chunks: list[dict]) -> str:
    llm = _get_llm()
    if llm is None:
        logger.warning("No LLM configured, returning chunk-based fallback")
        return _no_llm_fallback(question, chunks)

    start = time.perf_counter()

    context_parts = []
    for i, chunk in enumerate(chunks):
        doc_id = chunk.get("document_id", "?")
        text = chunk.get("text", "")
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
        logger.error("LLM generation failed (will use retrieved context): %s", e)
        logger.debug("LLM failure traceback:\n%s", traceback.format_exc())
        return _no_llm_fallback(question, chunks)


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


def _no_llm_fallback(question: str, chunks: list[dict]) -> str:
    if not chunks:
        return (
            "I don't have enough information to answer this question. "
            "Please upload relevant documents or rephrase your question."
        )

    top = chunks[0]
    snippet = top.get("text", "")[:300]
    doc_id = top.get("document_id", "unknown")

    return (
        f"Based on the retrieved documents (source: {doc_id}):\n\n"
        f"{snippet}\n\n"
        "_(LLM is unavailable. Displaying the most relevant retrieved content above.)_"
    )
