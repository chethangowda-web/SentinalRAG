"""Shared construction and invocation of the chat LLM.

Every LLM call in the app goes through here so provider quirks are handled in one place:

* per-minute rate limits (HTTP 429 with a short "retry in Ns") are waited out;
* transient 502/503/504 are retried;
* a *daily* quota ("retry in 6h30m") is not waited out: that model is marked exhausted, the next
  configured fallback model (each has its own allowance) is tried, and when none is left the call
  fails fast with LLMQuotaExhausted so users get a clear message instead of minutes of retries.
"""
import logging
import re
import threading
import time
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_DURATION = re.compile(r"retry in\s+((?:\d+(?:\.\d+)?\s*[hms]\s*)+)", re.IGNORECASE)
_DURATION_PART = re.compile(r"(\d+(?:\.\d+)?)\s*([hms])", re.IGNORECASE)
_UNIT_SECONDS = {"h": 3600.0, "m": 60.0, "s": 1.0}

# Wait at most this long for a per-minute limit to clear before giving up on a call.
MAX_RATE_LIMIT_WAIT_SECONDS = 40.0
# A provider wait longer than this means a daily cap, not a per-minute throttle.
DAILY_QUOTA_THRESHOLD_SECONDS = 300.0


class LLMQuotaExhausted(Exception):
    """Every configured model has used up its quota for now."""

    def __init__(self, retry_after_seconds: float):
        self.retry_after_seconds = retry_after_seconds
        hours = retry_after_seconds / 3600
        when = f"about {hours:.0f} hour(s)" if hours >= 1 else f"about {max(1, int(retry_after_seconds // 60))} minute(s)"
        super().__init__(f"The AI model's request quota is used up for now; it resets in {when}.")


def parse_retry_seconds(message: str) -> float | None:
    """Parse the provider's "Please retry in 6h30m2.3s" hint (any of h/m/s) into seconds."""
    match = _DURATION.search(message)
    if not match:
        return None
    return sum(float(n) * _UNIT_SECONDS[u.lower()] for n, u in _DURATION_PART.findall(match.group(1)))


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


def daily_quota_seconds(exc: Exception) -> float | None:
    """Seconds until a *daily* quota resets, or None if this error is not a daily-quota error."""
    if not is_rate_limit_error(exc):
        return None
    seconds = parse_retry_seconds(str(exc))
    if seconds is not None and seconds > DAILY_QUOTA_THRESHOLD_SECONDS:
        return seconds
    return None


# ---- exhausted-model bookkeeping (process-wide) ---------------------------------------------

_exhausted_until: dict[str, float] = {}
_state_lock = threading.Lock()
_concurrency = threading.BoundedSemaphore(max(1, settings.LLM_MAX_CONCURRENCY))


def _remaining(model: str) -> float:
    return max(0.0, _exhausted_until.get(model, 0.0) - time.monotonic())


def mark_exhausted(model: str, seconds: float) -> None:
    with _state_lock:
        _exhausted_until[model] = time.monotonic() + seconds
    logger.error("LLM model %s has used up its quota; retry in %.0f s", model, seconds)


def reset_exhausted() -> None:
    with _state_lock:
        _exhausted_until.clear()


def llm_status() -> dict:
    """Whether any model can still be called, for readiness checks and for refusing expensive jobs."""
    models = settings.llm_model_candidates
    if not settings.effective_llm_api_key or not models:
        return {"exhausted": False, "retry_after_seconds": 0, "models": models}
    remaining = [_remaining(m) for m in models]
    exhausted = all(r > 0 for r in remaining)
    return {"exhausted": exhausted, "retry_after_seconds": int(min(remaining)) if exhausted else 0, "models": models}


class FallbackLLM:
    """Calls the first model that still has quota; moves to the next when one runs out for the day."""

    def __init__(self, clients: dict[str, Any]):
        self._clients = clients

    def invoke(self, prompt: str):
        with _concurrency:
            for model, client in self._clients.items():
                if _remaining(model) > 0:
                    continue
                try:
                    return client.invoke(prompt)
                except Exception as exc:
                    seconds = daily_quota_seconds(exc)
                    if seconds is None:
                        raise
                    mark_exhausted(model, seconds)
        status = llm_status()
        raise LLMQuotaExhausted(status["retry_after_seconds"] or DAILY_QUOTA_THRESHOLD_SECONDS)


def build_llm(max_tokens: int, timeout: int, temperature: float | None = None):
    """Return a configured chat model, or None when no provider key is set."""
    if not settings.effective_llm_api_key:
        return None

    from langchain_openai import ChatOpenAI

    clients = {}
    for model in settings.llm_model_candidates:
        kwargs = {
            "model": model,
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
        clients[model] = ChatOpenAI(**kwargs)
    return FallbackLLM(clients)


def rate_limit_wait_seconds(exc: Exception, attempt: int) -> float:
    """How long to wait before retrying: the provider's hint if given, else a growing default."""
    hinted = parse_retry_seconds(str(exc))
    wait = hinted + 1.0 if hinted is not None else 10.0 * (attempt + 1)
    return min(wait, MAX_RATE_LIMIT_WAIT_SECONDS)


def invoke_with_retry(llm, prompt: str, rate_limit_retries: int = 1):
    """llm.invoke(prompt), waiting out per-minute limits and transient provider errors.

    A daily quota is never waited out: LLMQuotaExhausted propagates immediately.
    """
    for attempt in range(rate_limit_retries + 1):
        try:
            return llm.invoke(prompt)
        except LLMQuotaExhausted:
            raise
        except Exception as exc:
            retryable = is_rate_limit_error(exc) or is_transient_error(exc)
            if not retryable or attempt == rate_limit_retries:
                raise
            wait = rate_limit_wait_seconds(exc, attempt)
            logger.warning("LLM rate limited; waiting %.1fs before retry %d/%d", wait, attempt + 1, rate_limit_retries)
            time.sleep(wait)
    raise RuntimeError("unreachable")  # pragma: no cover
