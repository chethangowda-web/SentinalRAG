import hashlib
import logging
from difflib import SequenceMatcher
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document

logger = logging.getLogger(__name__)


def compute_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def compute_file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def filename_similarity(name1: str, name2: str) -> float:
    return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()


def _user_scope(user_id: str | None):
    # Duplicates are only ever reported against the uploader's own documents.
    if user_id is None:
        return Document.user_id.is_(None)
    return Document.user_id == user_id


async def check_duplicate(
    sha256: str,
    filename: str,
    db: AsyncSession,
    text_preview: str | None = None,
    user_id: str | None = None,
) -> dict | None:
    result = await db.execute(
        select(Document).where(Document.sha256_hash == sha256, _user_scope(user_id)).limit(1)
    )
    exact_match = result.scalars().first()
    if exact_match:
        return {
            "is_duplicate": True,
            "similarity": 99.0,
            "existing_id": exact_match.id,
            "existing_filename": exact_match.filename,
            "method": "exact_hash",
            "sha256": sha256,
        }

    result = await db.execute(
        select(Document).where(_user_scope(user_id)).order_by(Document.created_at.desc()).limit(50)
    )
    recent_docs = result.scalars().all()

    for doc in recent_docs:
        sim = filename_similarity(filename, doc.filename)
        if sim > 0.85:
            return {
                "is_duplicate": True,
                "similarity": round(sim * 100, 1),
                "existing_id": doc.id,
                "existing_filename": doc.filename,
                "method": "filename_similarity",
                "sha256": sha256,
            }

    if text_preview and len(text_preview) > 50:
        try:
            from qdrant_client.http.models import FieldCondition, Filter, MatchValue

            from app.core.qdrant import get_qdrant_client
            from app.services.embedding_service import generate_embeddings_async

            vectors = await generate_embeddings_async([text_preview[:500]])
            if vectors:
                client = get_qdrant_client()
                conditions = []
                if user_id is not None:
                    conditions.append(FieldCondition(key="user_id", match=MatchValue(value=user_id)))
                resp = client.query_points(
                    collection_name=settings.QDRANT_COLLECTION,
                    query=vectors[0],
                    query_filter=Filter(must=conditions) if conditions else None,
                    limit=5,
                    score_threshold=0.92,
                    with_payload=True,
                )
                for vr in resp.points:
                    doc_id = (vr.payload or {}).get("document_id", "")
                    if doc_id and vr.score > 0.95:
                        return {
                            "is_duplicate": True,
                            "similarity": round(vr.score * 100, 1),
                            "existing_id": doc_id,
                            "existing_filename": vr.payload.get("filename", "Unknown"),
                            "method": "embedding_similarity",
                            "sha256": sha256,
                        }
        except Exception as e:
            logger.warning("Vector duplicate check failed: %s", e)

    return None
