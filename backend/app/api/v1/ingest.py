import asyncio
import logging

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_session_maker
from app.core.exceptions import AppException
from app.models.document import Document
from app.schemas.document import IngestResponse
from app.services.document_service import ingest_document
from app.services.indexing_service import embed_document

logger = logging.getLogger(__name__)

router = APIRouter()

_auto_embed_tasks: set[asyncio.Task] = set()


async def _auto_embed(document_id: str):
    try:
        logger.info("Auto-embed starting for: %s", document_id)
        session_maker = get_session_maker()
        async with session_maker() as bg_db:
            result = await embed_document(document_id, bg_db)
            logger.info("Auto-embed completed for %s: status=%s", document_id, result.status)
    except Exception as e:
        logger.exception("Auto-embed failed for %s: %s", document_id, e)


@router.post("/ingest", response_model=IngestResponse)
async def upload_document(file: UploadFile | None = None, db: AsyncSession = Depends(get_db)):
    if file is None:
        raise AppException(status_code=400, detail="No file provided. Send a file as multipart/form-data.")

    if not file.filename:
        raise AppException(status_code=400, detail="No file provided")

    filename = file.filename
    content_type = file.content_type or "application/octet-stream"
    file_bytes = await file.read()

    logger.info("Ingest request: filename=%s content_type=%s size=%d", filename, content_type, len(file_bytes))

    try:
        result = await ingest_document(filename, content_type, file_bytes, db)
    except AppException:
        raise
    except Exception as exc:
        logger.exception("Unhandled error in upload_document")
        raise AppException(status_code=500, detail=f"Unhandled error: {exc}")

    task = asyncio.create_task(_auto_embed(result.document_id))
    _auto_embed_tasks.add(task)
    task.add_done_callback(_auto_embed_tasks.discard)

    return result
