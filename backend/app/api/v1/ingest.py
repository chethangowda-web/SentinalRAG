import logging
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.exceptions import AppException
from app.models.user import User
from app.schemas.document import IngestResponse
from app.services.document_service import ingest_document

logger = logging.getLogger(__name__)

router = APIRouter()


def _content_type_from_ext(ext: str) -> str:
    mapping = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    return mapping.get(ext, "application/octet-stream")


@router.post("/ingest", response_model=IngestResponse)
async def upload_document(
    file: UploadFile | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file is None:
        raise AppException(status_code=400, detail="No file provided. Send a file as multipart/form-data.")

    if not file.filename:
        raise AppException(status_code=400, detail="No file provided")

    filename = file.filename
    ext = Path(filename).suffix.lower()
    content_type = file.content_type or _content_type_from_ext(ext)
    file_bytes = await file.read()

    logger.info("Ingest request: filename=%s content_type=%s size=%d", filename, content_type, len(file_bytes))

    try:
        result = await ingest_document(filename, content_type, file_bytes, db, user_id=current_user.id)
    except AppException:
        raise
    except Exception as exc:
        logger.exception("Unhandled error in upload_document")
        raise AppException(status_code=500, detail=f"Unhandled error: {exc}")

    return result
