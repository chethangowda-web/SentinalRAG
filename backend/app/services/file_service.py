import logging
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import AppException, InvalidUploadError

logger = logging.getLogger(__name__)

_PDF_MAGIC = b"%PDF-"


def validate_file(filename: str, content_type: str, file_size: int, file_bytes: bytes = b"") -> None:
    ext = Path(filename).suffix.lower()

    if ext not in settings.ALLOWED_EXTENSIONS:
        raise AppException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(settings.ALLOWED_EXTENSIONS))}",
        )

    if content_type not in settings.ALLOWED_CONTENT_TYPES:
        raise AppException(
            status_code=415,
            detail=f"Unsupported content type '{content_type}'. Allowed: application/pdf, image/png, image/jpeg",
        )

    if file_size > settings.MAX_FILE_SIZE:
        raise AppException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {settings.MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )

    if file_size == 0 or (file_bytes and not file_bytes.strip()):
        raise InvalidUploadError(detail="Uploaded file is empty. Please provide a non-empty file.")

    if ext == ".pdf" and len(file_bytes) >= 5 and not file_bytes.startswith(_PDF_MAGIC):
        raise InvalidUploadError(
            detail="File is not a valid PDF (missing PDF header).",
        )

    logger.info("File validation passed: %s (%s, %d bytes)", filename, content_type, file_size)


async def save_upload(file_bytes: bytes, dest_path: Path) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(file_bytes)
    logger.info("File saved to %s (%d bytes)", dest_path, len(file_bytes))
