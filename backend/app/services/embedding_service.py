import logging
import time

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

_model = None
_model_name = None


def _load_model():
    global _model, _model_name
    if _model is None or _model_name != settings.EMBEDDING_MODEL:
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL)
        start = time.perf_counter()
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        _model_name = settings.EMBEDDING_MODEL
        elapsed = round(time.perf_counter() - start, 2)
        logger.info("Model loaded in %.2f seconds", elapsed)
    return _model


def normalize_embedding(vector: list[float]) -> list[float]:
    arr = np.array(vector, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm > 0:
        arr = arr / norm
    return arr.tolist()


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    model = _load_model()
    batch_size = settings.EMBEDDING_BATCH_SIZE
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        batch_start = time.perf_counter()

        raw = model.encode(batch, show_progress_bar=False)
        normalized = [normalize_embedding(vec.tolist()) for vec in raw]

        batch_elapsed = round(time.perf_counter() - batch_start, 3)
        logger.info(
            "Embedding batch %d/%d: %d texts, %.3fs (%.1f ms/text)",
            i // batch_size + 1,
            (len(texts) + batch_size - 1) // batch_size,
            len(batch),
            batch_elapsed,
            batch_elapsed / len(batch) * 1000 if batch else 0,
        )
        all_embeddings.extend(normalized)

    total_elapsed = round(time.perf_counter() - batch_start if len(texts) <= batch_size else 0, 2)
    logger.info("Embedding complete: %d vectors generated", len(all_embeddings))
    return all_embeddings
