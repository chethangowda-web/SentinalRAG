import logging
import time

from app.core.config import settings
from app.services.model_loading import load_lock

logger = logging.getLogger(__name__)

_model = None
_model_name = None
_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _load_reranker():
    if _model is None or _model_name != _RERANKER_MODEL:
        with load_lock:
            _load_reranker_locked()
    return _model


def _load_reranker_locked():
    global _model, _model_name
    if _model is None or _model_name != _RERANKER_MODEL:
        import torch
        torch.set_num_threads(1)

        from sentence_transformers import CrossEncoder

        logger.info("Loading cross-encoder model: %s", _RERANKER_MODEL)
        start = time.perf_counter()
        _model = CrossEncoder(_RERANKER_MODEL, device="cpu", max_length=settings.RERANK_MAX_TOKENS)
        _model_name = _RERANKER_MODEL
        elapsed = round(time.perf_counter() - start, 2)
        logger.info("Cross-encoder loaded in %.2f seconds", elapsed)
    return _model


def rerank(
    query: str,
    texts: list[str],
    top_k: int | None = None,
) -> list[tuple[int, float]]:
    if not texts:
        return []

    start = time.perf_counter()
    model = _load_reranker()

    pairs = [[query, text] for text in texts]

    import torch
    with torch.no_grad():
        scores = model.predict(pairs, show_progress_bar=False)

    scored: list[tuple[int, float]] = [
        (i, round(float(score), 4)) for i, score in enumerate(scores)
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    if top_k is not None:
        scored = scored[:top_k]

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        "Reranker: %.1fms for %d candidates, top score=%.4f",
        elapsed, len(texts), scored[0][1] if scored else 0.0,
    )

    return scored
