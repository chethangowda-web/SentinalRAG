import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

from app.core.config import settings


def generate_document_id() -> str:
    return str(uuid.uuid4())


def get_upload_path(original_filename: str) -> Tuple[Path, str]:
    now = datetime.now(timezone.utc)
    year = str(now.year)
    month = f"{now.month:02d}"
    doc_id = generate_document_id()
    ext = Path(original_filename).suffix.lower()
    stored_name = f"{doc_id}{ext}"
    upload_dir = settings.UPLOAD_DIR / year / month
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir / stored_name, doc_id


def get_processed_path(document_id: str) -> Path:
    processed_dir = settings.PROCESSED_DIR
    processed_dir.mkdir(parents=True, exist_ok=True)
    return processed_dir / f"{document_id}.txt"
