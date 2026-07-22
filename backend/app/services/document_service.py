import logging
import time
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException, InvalidUploadError
from app.models.document import Document
from app.schemas.document import IngestResponse
from app.services.document_summary_service import generate_document_summary
from app.services.duplicate_detection_service import check_duplicate
from app.services.file_service import save_upload, validate_file
from app.services.ocr_quality_service import analyze_ocr_quality
from app.services.ocr_service import ocr_image, ocr_pdf
from app.services.text_cleaning import clean_text
from app.utils.file_utils import get_processed_path, get_upload_path

try:
    import fitz

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def _determine_strategy(ext: str) -> str:
    if ext in IMAGE_EXTENSIONS:
        return "ocr_image"
    return "pdf"


def _extract_pdf_text(pdf_path: Path) -> tuple[str, int, bool]:
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError("PyMuPDF is not available")

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as e:
        raise InvalidUploadError(detail=f"Cannot process PDF file: {e}")
    total_pages = len(doc)
    raw_text_parts: list[str] = []
    ocr_used = False

    for page_num in range(total_pages):
        page = doc[page_num]
        text = page.get_text()
        raw_text_parts.append(text)

    doc.close()
    combined = "\n".join(raw_text_parts)

    if len(combined.strip()) < settings.TEXT_MIN_LENGTH_FOR_PDF:
        logger.info("PDF appears scanned — falling back to OCR (%d chars)", len(combined.strip()))
        combined = ocr_pdf(pdf_path)
        ocr_used = True

    return combined, total_pages, ocr_used


def _process_image(image_path: Path) -> tuple[str, int, bool]:
    text = ocr_image(image_path)
    return text, 1, True


async def ingest_document(
    filename: str,
    content_type: str,
    file_bytes: bytes,
    db: AsyncSession,
) -> IngestResponse:
    file_size = len(file_bytes)

    validate_file(filename, content_type, file_size, file_bytes)

    ext = Path(filename).suffix.lower()
    upload_path, doc_id = get_upload_path(filename)
    processed_path = get_processed_path(doc_id)

    await save_upload(file_bytes, upload_path)

    strategy = _determine_strategy(ext)
    logger.info("Processing strategy: %s for %s", strategy, filename)

    start_time = time.perf_counter()

    try:
        if strategy == "ocr_image":
            raw_text, pages, ocr_used = _process_image(upload_path)
        else:
            raw_text, pages, ocr_used = _extract_pdf_text(upload_path)
    except (InvalidUploadError, AppException):
        raise
    except Exception as exc:
        raise AppException(status_code=500, detail=f"Processing failed: {exc}")

    cleaned = clean_text(raw_text)

    with open(processed_path, "w", encoding="utf-8") as f:
        f.write(cleaned)

    word_count = len(cleaned.split())
    char_count = len(cleaned)
    elapsed = round(time.perf_counter() - start_time, 2)

    ocr_result = None
    if ocr_used or ext in IMAGE_EXTENSIONS:
        ocr_result = analyze_ocr_quality(cleaned, pages)
        logger.info("OCR quality: %s (confidence=%.1f)", ocr_result["quality"], ocr_result["confidence"])

    summary_result = await generate_document_summary(cleaned, filename)
    logger.info("Summary generated for %s: type=%s topics=%d", doc_id, summary_result["document_type"], len(summary_result["key_topics"]))

    duplicate_result = await check_duplicate(file_bytes, filename, db, cleaned[:200])
    if duplicate_result:
        logger.warning("Duplicate detected: %s matches %s (method=%s, sim=%.1f%%)", filename, duplicate_result.get("existing_filename", ""), duplicate_result["method"], duplicate_result["similarity"])

    document = Document(
        id=doc_id,
        filename=filename,
        file_type=ext.lstrip("."),
        status="processed",
        original_path=str(upload_path),
        extracted_text_path=str(processed_path),
        pages=pages,
        word_count=word_count,
        char_count=char_count,
        ocr_used=ocr_used,
        file_size=file_size,
        text_content=cleaned,
        processing_time=elapsed,
        ocr_quality=ocr_result["quality"] if ocr_result else None,
        ocr_confidence=ocr_result["confidence"] if ocr_result else None,
        summary=summary_result["summary"],
        key_topics=",".join(summary_result["key_topics"][:8]) if summary_result.get("key_topics") else None,
        keywords=",".join(summary_result["keywords"][:12]) if summary_result.get("keywords") else None,
        document_type=summary_result["document_type"],
        estimated_reading_time=summary_result["estimated_reading_time"],
        sha256_hash=duplicate_result["sha256"] if duplicate_result else None,
        duplicate_of=duplicate_result["existing_id"] if duplicate_result and duplicate_result["similarity"] > 90 else None,
    )

    try:
        db.add(document)
        await db.commit()
        await db.refresh(document)
    except Exception as exc:
        logger.exception("Database error while saving document %s", doc_id)
        raise AppException(status_code=500, detail=f"Failed to save document to database: {exc}")

    logger.info(
        "Document ingested: id=%s pages=%d words=%d ocr=%s time=%.2fs",
        doc_id, pages, word_count, ocr_used, elapsed,
    )

    return IngestResponse(
        document_id=doc_id,
        status="processed",
        pages=pages,
        words=word_count,
        ocr_used=ocr_used,
        processing_time=elapsed,
        ocr_quality=ocr_result["quality"] if ocr_result else None,
        ocr_confidence=ocr_result["confidence"] if ocr_result else None,
        summary=summary_result["summary"],
        document_type=summary_result["document_type"],
        estimated_reading_time=summary_result["estimated_reading_time"],
        is_duplicate=duplicate_result is not None,
        duplicate_info={
            "existing_id": duplicate_result["existing_id"],
            "existing_filename": duplicate_result["existing_filename"],
            "similarity": duplicate_result["similarity"],
            "method": duplicate_result["method"],
        } if duplicate_result else None,
    )
