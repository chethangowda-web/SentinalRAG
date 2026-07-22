import asyncio
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_session_maker
from app.models.chunk import Chunk
from app.schemas.chunk import ChunkListResponse, ChunkMetadata, EmbedResponse
from app.services.indexing_service import embed_document

logger = logging.getLogger(__name__)

router = APIRouter()

_tasks: set[asyncio.Task] = set()


async def _background_embed(document_id: str):
    try:
        logger.info("Background embed starting for: %s", document_id)
        session_maker = get_session_maker()
        async with session_maker() as bg_db:
            await embed_document(document_id, bg_db)
        logger.info("Background embed completed for: %s", document_id)
    except Exception as e:
        logger.exception("Background embed failed for %s: %s", document_id, e)


@router.post("/embed/{document_id}", response_model=EmbedResponse)
async def embed_document_endpoint(document_id: str, db: AsyncSession = Depends(get_db)):
    logger.info("Embed request for document: %s", document_id)
    task = asyncio.create_task(_background_embed(document_id))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return EmbedResponse(
        document_id=document_id,
        total_chunks=0,
        embedded_chunks=0,
        status="processing",
    )


@router.get("/document/{document_id}/chunks", response_model=ChunkListResponse)
async def list_chunks(document_id: str, db: AsyncSession = Depends(get_db)):
    logger.info("List chunks request for document: %s", document_id)

    count_result = await db.execute(
        select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id)
    )
    total = count_result.scalar() or 0

    if total == 0:
        raise AppException(status_code=404, detail=f"No chunks found for document {document_id}")

    result = await db.execute(
        select(Chunk)
        .where(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index)
    )
    chunks = result.scalars().all()

    return ChunkListResponse(
        document_id=document_id,
        total_chunks=total,
        chunks=[
            ChunkMetadata(
                id=c.id,
                document_id=c.document_id,
                chunk_index=c.chunk_index,
                chunk_text=c.chunk_text,
                char_start=c.char_start,
                char_end=c.char_end,
                word_count=c.word_count,
                page_number=c.page_number,
                embedding_status=c.embedding_status,
            )
            for c in chunks
        ],
    )
