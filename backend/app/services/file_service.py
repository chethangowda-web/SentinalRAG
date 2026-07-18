import logging
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import AppException

logger = logging.getLogger(__name__)


def validate_file(filename: str, content_type: str, file_size: int) -> None:
    ext = Path(filename).suffix.lower()

    if ext not in settings.ALLOWED_EXTENSIONS:
        raise AppException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(settings.ALLOWED_EXTENSIONS))}",
        )

    if content_type not in settings.ALLOWED_CONTENT_TYPES:
        raise AppException(
            status_code=400,
            detail=f"Unsupported content type '{content_type}'.",
        )

    if file_size > settings.MAX_FILE_SIZE:
        raise AppException(
            status_code=400,
            detail=f"File too large. Maximum allowed size is {settings.MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )

    logger.info("File validation passed: %s (%s, %d bytes)", filename, content_type, file_size)


async def save_upload(file_bytes: bytes, dest_path: Path) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(file_bytes)
    logger.info("File saved to %s (%d bytes)", dest_path, len(file_bytes))
