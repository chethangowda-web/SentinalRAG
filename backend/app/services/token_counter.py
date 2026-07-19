import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

_ENCODING = None


@lru_cache(maxsize=1)
def _get_encoding():
    global _ENCODING
    try:
        import tiktoken
        _ENCODING = tiktoken.get_encoding("cl100k_base")
        logger.info("tiktoken encoding initialized: cl100k_base")
    except Exception as e:
        logger.warning("tiktoken not available, using fallback estimator: %s", e)
        _ENCODING = None
    return _ENCODING


def count_tokens(text: str) -> int:
    encoding = _get_encoding()
    if encoding is not None:
        try:
            return len(encoding.encode(text))
        except Exception:
            pass
    return len(text) // 4


def count_tokens_batch(texts: list[str]) -> int:
    return sum(count_tokens(t) for t in texts)
