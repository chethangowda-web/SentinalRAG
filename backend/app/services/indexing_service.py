import gc
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException
from app.models.chunk import Chunk
from app.models.document import Document
from app.schemas.chunk import EmbedResponse
from app.services.chunking_service import TextChunk, chunk_text
from app.services.embedding_service import generate_embeddings_async
from app.services.qdrant_service import ensure_collection, upsert_vectors, vector_exists
from app.utils.memory import force_gc, log_memory_usage

logger = logging.getLogger(__name__)


async def embed_document(document_id: str, db: AsyncSession) -> EmbedResponse:
    mem_before = log_memory_usage("embedding_start")

    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if document is None:
        logger.error("Document %s not found for embedding", document_id)
        raise AppException(status_code=404, detail=f"Document {document_id} not found")

    if document.status == "embedded":
        logger.info("Document %s already embedded, skipping", document_id)
        return EmbedResponse(
            document_id=document_id,
            total_chunks=0,
            embedded_chunks=0,
            status="embedded",
        )

    text = document.text_content
    if not text:
        text_path_str = document.extracted_text_path
        if text_path_str:
            text_path = Path(text_path_str)
            if text_path.exists():
                with open(text_path, "r", encoding="utf-8") as f:
                    text = f.read()
        if not text:
            raise AppException(status_code=400, detail="Document has no text content")

    if not text.strip():
        raise AppException(status_code=400, detail="Document text is empty")

    chunks = chunk_text(text)
    text = None
    logger.info("Created %d chunks for document %s", len(chunks), document_id)
    log_memory_usage("chunking_done", mem_before)

    ensure_collection()

    processed_chunks = 0
    total_chunks = len(chunks)
    batch_size = max(16, min(settings.EMBEDDING_BATCH_SIZE, 32))

    for batch_start in range(0, len(chunks), batch_size):
        batch_end = min(batch_start + batch_size, len(chunks))
        batch_chunks = chunks[batch_start:batch_end]

        chunk_records: list[Chunk] = []
        texts_for_embedding: list[str] = []
        payloads: list[dict] = []

        for tc in batch_chunks:
            if vector_exists(document_id, tc.chunk_index):
                logger.info("Skipping existing chunk %d for document %s", tc.chunk_index, document_id)
                continue

            token_count = int(tc.word_count * 1.3)
            chunk_records.append(
                Chunk(
                    id=tc.chunk_id,
                    document_id=document_id,
                    chunk_index=tc.chunk_index,
                    chunk_text=tc.text,
                    char_start=tc.char_start,
                    char_end=tc.char_end,
                    word_count=tc.word_count,
                    page_number=tc.page_number,
                    embedding_status="pending",
                )
            )
            texts_for_embedding.append(tc.text)
            payloads.append({
                "document_id": document_id,
                "chunk_id": tc.chunk_id,
                "chunk_index": tc.chunk_index,
                "filename": document.filename,
                "page_number": tc.page_number,
                "section": tc.section,
                "word_count": tc.word_count,
                "token_count": token_count,
                "text": tc.text,
                "user_id": document.user_id,
            })

        if not texts_for_embedding:
            continue

        try:
            vectors = await generate_embeddings_async(texts_for_embedding)
            texts_for_embedding = None

            point_ids = upsert_vectors(vectors, payloads)
            vectors = None
            payloads = None

            for i, chunk_rec in enumerate(chunk_records):
                chunk_rec.vector_id = point_ids[i]
                chunk_rec.embedding_status = "embedded"
                db.add(chunk_rec)

            processed_chunks += len(chunk_records)
            chunk_records = None
            gc.collect()

            logger.info(
                "Batch %d/%d: embedded %d chunks for document %s",
                batch_start // batch_size + 1,
                (total_chunks + batch_size - 1) // batch_size,
                len(point_ids),
                document_id,
            )
        except Exception:
            logger.exception("Embedding failed for document %s, cleaning up", document_id)
            document.status = "failed"
            await db.commit()
            raise AppException(status_code=500, detail=f"Embedding failed for document {document_id}")

    document.status = "embedded"
    await db.commit()

    logger.info(
        "Document %s embedded: %d chunks, %d vectors",
        document_id, total_chunks, processed_chunks,
    )

    force_gc()
    log_memory_usage("embedding_done", mem_before)

    return EmbedResponse(
        document_id=document_id,
        total_chunks=total_chunks,
        embedded_chunks=processed_chunks,
        status="embedded",
    )
