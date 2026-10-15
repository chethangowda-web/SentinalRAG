"""Shared construction and invocation of the chat LLM.

Every LLM call in the app goes through here so provider quirks are handled in one place:
free-tier rate limits (HTTP 429) are waited out instead of failing the whole answer.
"""
import logging
import re
import time

from app.core.config import settings

logger = logging.getLogger(__name__)

_RETRY_IN_SECONDS = re.compile(r"retry in ([0-9]+(?:\.[0-9]+)?)\s*s", re.IGNORECASE)

# Wait at most this long for a rate limit to clear before giving up on a call.
MAX_RATE_LIMIT_WAIT_SECONDS = 40.0


def build_llm(max_tokens: int, timeout: int, temperature: float | None = None):
    """Return a configured chat model, or None when no provider key is set."""
    if not settings.effective_llm_api_key:
        return None

    from langchain_openai import ChatOpenAI

    kwargs = {
        "model": settings.effective_llm_model,
        "api_key": settings.effective_llm_api_key,
        "base_url": settings.effective_llm_base_url,
        "temperature": settings.LLM_TEMPERATURE if temperature is None else temperature,
        "max_tokens": max_tokens,
        "timeout": timeout,
        # Rate limits are handled by invoke_with_retry, which can honour the provider's
        # "retry in Ns" hint; the client's own immediate retry would only burn quota.
        "max_retries": 0,
    }
    if settings.effective_llm_reasoning_effort:
        kwargs["reasoning_effort"] = settings.effective_llm_reasoning_effort
    return ChatOpenAI(**kwargs)


def is_rate_limit_error(exc: Exception) -> bool:
    return getattr(exc, "status_code", None) == 429 or "429" in str(exc)[:200]


# 502/503/504 are the provider saying "try again" (Gemini: "model is experiencing high demand").
_TRANSIENT_STATUS = (502, 503, 504)


def is_transient_error(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None)
    if status in _TRANSIENT_STATUS:
        return True
    head = str(exc)[:200]
    return any(f"Error code: {code}" in head for code in _TRANSIENT_STATUS)


def rate_limit_wait_seconds(exc: Exception, attempt: int) -> float:
    """How long to wait before retrying: the provider's hint if given, else a growing default."""
    match = _RETRY_IN_SECONDS.search(str(exc))
    hinted = float(match.group(1)) + 1.0 if match else 10.0 * (attempt + 1)
    return min(hinted, MAX_RATE_LIMIT_WAIT_SECONDS)


def invoke_with_retry(llm, prompt: str, rate_limit_retries: int = 1):
    """llm.invoke(prompt), waiting out rate limits and transient provider errors up to `rate_limit_retries` times."""
    for attempt in range(rate_limit_retries + 1):
        try:
            return llm.invoke(prompt)
        except Exception as exc:
            retryable = is_rate_limit_error(exc) or is_transient_error(exc)
            if not retryable or attempt == rate_limit_retries:
                raise
            wait = rate_limit_wait_seconds(exc, attempt)
            logger.warning("LLM rate limited; waiting %.1fs before retry %d/%d", wait, attempt + 1, rate_limit_retries)
            time.sleep(wait)
    raise RuntimeError("unreachable")  # pragma: no cover
