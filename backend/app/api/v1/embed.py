import asyncio
import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_session_maker
from app.core.exceptions import AppException
from app.models.chunk import Chunk
from app.schemas.chunk import ChunkListResponse, ChunkMetadata, EmbedResponse
from app.services.indexing_service import embed_document

logger = logging.getLogger(__name__)

router = APIRouter()

_auto_eval_tasks: set[asyncio.Task] = set()


async def _auto_run_evaluation():
    try:
        from app.api.v1.evaluation import run_evaluation
        result = await run_evaluation()
        logger.info("Auto-evaluation triggered: %s", result.get("evaluation_id"))
    except Exception as e:
        logger.warning("Auto-evaluation trigger skipped: %s", e)


@router.post("/embed/{document_id}", response_model=EmbedResponse)
async def embed_document_endpoint(document_id: str, db: AsyncSession = Depends(get_db)):
    logger.info("Embed request for document: %s", document_id)
    try:
        result = await embed_document(document_id, db)
    except AppException:
        raise
    except Exception as e:
        logger.exception("Embed failed for document %s", document_id)
        raise AppException(status_code=500, detail=f"Embedding failed: {e}")

    task = asyncio.create_task(_auto_run_evaluation())
    _auto_eval_tasks.add(task)
    task.add_done_callback(_auto_eval_tasks.discard)

    return result


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
