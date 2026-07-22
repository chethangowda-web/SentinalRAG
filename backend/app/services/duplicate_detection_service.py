import hashlib
import logging
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document

logger = logging.getLogger(__name__)


def compute_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def filename_similarity(name1: str, name2: str) -> float:
    return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()


async def check_duplicate(
    file_bytes: bytes,
    filename: str,
    db: AsyncSession,
    text_preview: str | None = None,
) -> dict | None:
    sha256 = compute_sha256(file_bytes)

    result = await db.execute(
        select(Document).where(Document.sha256_hash == sha256).limit(1)
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
        select(Document).order_by(Document.created_at.desc()).limit(50)
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
            from app.core.qdrant import get_qdrant_client
            from app.services.embedding_service import generate_embeddings

            vectors = generate_embeddings([text_preview[:500]])
            if vectors:
                client = get_qdrant_client()
                qdrant_results = client.search(
                    collection_name="documents",
                    query_vector=vectors[0],
                    limit=5,
                    score_threshold=0.92,
                    with_payload=True,
                )
                for vr in qdrant_results:
                    doc_id = vr.payload.get("document_id", "")
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
