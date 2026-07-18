import logging
import uuid
from typing import Any

from qdrant_client.http import models as qmodels
from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import settings
from app.core.qdrant import get_qdrant_client

logger = logging.getLogger(__name__)


def ensure_collection() -> None:
    client = get_qdrant_client()
    collections = client.get_collections().collections
    existing = {c.name for c in collections}

    if settings.QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=qmodels.VectorParams(
                size=settings.EMBEDDING_DIMENSION,
                distance=qmodels.Distance.COSINE,
            ),
        )
        logger.info("Created Qdrant collection: %s", settings.QDRANT_COLLECTION)
    else:
        logger.info("Qdrant collection already exists: %s", settings.QDRANT_COLLECTION)


def upsert_vectors(
    vectors: list[list[float]],
    payloads: list[dict[str, Any]],
) -> list[str]:
    if not vectors or not payloads:
        return []

    client = get_qdrant_client()
    ensure_collection()

    point_ids: list[str] = []
    points: list[qmodels.PointStruct] = []

    for vec, payload in zip(vectors, payloads):
        point_id = str(uuid.uuid4())
        point_ids.append(point_id)
        points.append(
            qmodels.PointStruct(
                id=point_id,
                vector=vec,
                payload=payload,
            )
        )

    client.upsert(
        collection_name=settings.QDRANT_COLLECTION,
        points=points,
    )

    logger.info("Upserted %d vectors to Qdrant collection '%s'", len(points), settings.QDRANT_COLLECTION)
    return point_ids


def vector_exists(document_id: str, chunk_index: int) -> bool:
    client = get_qdrant_client()
    try:
        result = client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            scroll_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=document_id),
                    ),
                    qmodels.FieldCondition(
                        key="chunk_index",
                        match=qmodels.MatchValue(value=chunk_index),
                    ),
                ]
            ),
            limit=1,
        )
        return len(result[0]) > 0
    except UnexpectedResponse:
        return False
