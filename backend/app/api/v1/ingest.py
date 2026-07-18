import logging

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.schemas.document import IngestResponse
from app.services.document_service import ingest_document

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def upload_document(file: UploadFile, db: AsyncSession = Depends(get_db)):
    if not file.filename:
        raise AppException(status_code=400, detail="No file provided")

    filename = file.filename
    content_type = file.content_type or "application/octet-stream"
    file_bytes = await file.read()

    logger.info("Ingest request: filename=%s content_type=%s size=%d", filename, content_type, len(file_bytes))

    result = await ingest_document(filename, content_type, file_bytes, db)
    return result
