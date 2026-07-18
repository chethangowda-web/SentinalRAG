import logging
import re
import time

logger = logging.getLogger(__name__)

_PUNCTUATION_RE = re.compile(r"[^\w\s.\-_:/@#+]")
_WHITESPACE_RE = re.compile(r"\s+")


def preprocess_query(raw_query: str) -> str:
    start = time.perf_counter()

    if not raw_query or not raw_query.strip():
        logger.warning("Empty query received")
        return ""

    query = raw_query.strip()
    query = query.lower()
    query = _PUNCTUATION_RE.sub(" ", query)
    query = _WHITESPACE_RE.sub(" ", query).strip()

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    logger.info("Query preprocessed in %.1fms: '%s' -> '%s'", elapsed, raw_query[:60], query[:120])

    return query
