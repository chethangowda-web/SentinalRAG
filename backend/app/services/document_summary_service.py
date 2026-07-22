import asyncio
import json
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


async def generate_document_summary(text: str, filename: str) -> dict:
    if not text or len(text.strip()) < 20:
        return {
            "summary": "Document is too short to summarize.",
            "key_topics": [],
            "keywords": [],
            "document_type": "unknown",
            "estimated_reading_time": 0,
        }

    llm = _get_llm()
    if llm is None:
        return _estimate_basic(text, filename)

    prompt = (
        "Analyze the following document text and return a JSON object with these fields:\n"
        "- summary: a 2-3 sentence summary\n"
        "- key_topics: array of 3-6 main topics\n"
        "- keywords: array of 5-10 key terms\n"
        "- document_type: one of: research_paper, report, contract, invoice, letter, article, manual, email, presentation, notes, other\n"
        "- estimated_reading_time: integer minutes (average 200 words/min)\n\n"
        "Return ONLY valid JSON, no markdown, no code fences.\n\n"
        f"Filename: {filename}\n\n"
        f"Text (first 8000 chars):\n{text[:8000]}"
    )

    try:
        response = await asyncio.to_thread(llm.invoke, prompt)
        content = response.content.strip()
        content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        result = json.loads(content)
        result.setdefault("summary", "Summary not available.")
        result.setdefault("key_topics", [])
        result.setdefault("keywords", [])
        result.setdefault("document_type", "other")
        result.setdefault("estimated_reading_time", max(len(text.split()) // 200, 1))
        return result
    except Exception as e:
        logger.warning("LLM summary failed: %s", e)
        return _estimate_basic(text, filename)


def _estimate_basic(text: str, filename: str) -> dict:
    words = text.split()
    word_count = len(words)
    reading_time = max(word_count // 200, 1)

    topics = _extract_topics_basic(text)

    return {
        "summary": f"Document '{filename}' contains approximately {word_count} words across {reading_time} minute(s) of estimated reading time.",
        "key_topics": topics[:5],
        "keywords": sorted(set(w.lower() for w in words if len(w) > 6))[:10],
        "document_type": _guess_document_type(filename, text),
        "estimated_reading_time": reading_time,
    }


def _extract_topics_basic(text: str) -> list[str]:
    words = text.lower().split()
    freq: dict[str, int] = {}
    for w in words:
        if len(w) > 5 and w.isalpha():
            freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: -x[1])
    return [w for w, _ in sorted_words[:8]]


def _guess_document_type(filename: str, text: str) -> str:
    name_lower = filename.lower()
    text_lower = text[:2000].lower()
    if "report" in name_lower or "report" in text_lower[:500]:
        return "report"
    if "contract" in name_lower or "agreement" in name_lower:
        return "contract"
    if "invoice" in name_lower or "bill" in name_lower:
        return "invoice"
    if "manual" in name_lower or "guide" in name_lower:
        return "manual"
    if "letter" in name_lower:
        return "letter"
    if "presentation" in name_lower or "slide" in name_lower:
        return "presentation"
    if "email" in name_lower:
        return "email"
    if "paper" in name_lower or "research" in text_lower[:300]:
        return "research_paper"
    if "note" in name_lower or "notes" in name_lower:
        return "notes"
    if "article" in name_lower:
        return "article"
    return "other"


def _get_llm():
    if not settings.effective_llm_api_key:
        return None
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.effective_llm_model,
        api_key=settings.effective_llm_api_key,
        base_url=settings.effective_llm_base_url,
        temperature=0.1,
        max_tokens=512,
    )
