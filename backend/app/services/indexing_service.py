import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.chunk import Chunk
from app.models.document import Document
from app.schemas.chunk import EmbedResponse
from app.services.chunking_service import TextChunk, chunk_text
from app.services.embedding_service import generate_embeddings_async
from app.services.qdrant_service import ensure_collection, upsert_vectors, vector_exists

logger = logging.getLogger(__name__)


async def embed_document(document_id: str, db: AsyncSession) -> EmbedResponse:
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if document is None:
        raise AppException(status_code=404, detail=f"Document {document_id} not found")

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
    logger.info("Created %d chunks for document %s", len(chunks), document_id)

    ensure_collection()

    chunk_records: list[Chunk] = []
    texts_for_embedding: list[str] = []
    payloads: list[dict] = []
    chunk_refs: list[TextChunk] = []

    for tc in chunks:
        exists = vector_exists(document_id, tc.chunk_index)
        if exists:
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
        })
        chunk_refs.append(tc)

    if not texts_for_embedding:
        return EmbedResponse(
            document_id=document_id,
            total_chunks=len(chunks),
            embedded_chunks=0,
            status="skipped",
        )

    vectors = await generate_embeddings_async(texts_for_embedding)

    point_ids = upsert_vectors(vectors, payloads)

    for i, chunk_rec in enumerate(chunk_records):
        chunk_rec.vector_id = point_ids[i]
        chunk_rec.embedding_status = "embedded"
        db.add(chunk_rec)

    document.status = "embedded"
    await db.commit()

    logger.info(
        "Document %s embedded: %d chunks, %d vectors",
        document_id, len(chunks), len(point_ids),
    )

    return EmbedResponse(
        document_id=document_id,
        total_chunks=len(chunks),
        embedded_chunks=len(point_ids),
        status="embedded",
    )
