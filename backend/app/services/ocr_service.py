import gc
import io
import logging
from pathlib import Path

from app.core.config import settings
from app.utils.memory import force_gc, log_memory_usage

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from PIL import Image

    TESSERACT_AVAILABLE = True
except Exception:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract or Pillow not available — OCR unavailable")


try:
    import fitz

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not installed")


def ocr_image(image_path: Path | bytes) -> str:
    if not TESSERACT_AVAILABLE:
        raise RuntimeError("OCR is not available — pytesseract/Pillow not installed")

    if isinstance(image_path, bytes):
        image = Image.open(io.BytesIO(image_path))
    else:
        image = Image.open(image_path)
    try:
        text = pytesseract.image_to_string(image, lang=settings.OCR_LANGUAGE)
    finally:
        image.close()
    logger.info("OCR completed for %s (%d chars)", image_path if isinstance(image_path, Path) else "bytes", len(text))
    return text


def ocr_pdf(pdf_path: Path) -> str:
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError("PyMuPDF is not available")

    if not TESSERACT_AVAILABLE:
        raise RuntimeError("OCR is not available — pytesseract/Pillow not installed")

    mem_before = log_memory_usage("ocr_start")

    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    all_text: list[str] = []

    logger.info("Starting OCR for scanned PDF: %s (%d pages)", pdf_path, total_pages)

    for page_num in range(total_pages):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=300)
        img_data = pix.tobytes("png")
        pix = None
        page = None
        try:
            text = ocr_image(img_data)
            all_text.append(text)
        finally:
            img_data = None

        if page_num % 5 == 0:
            gc.collect()

    doc.close()
    combined = "\n".join(all_text)
    logger.info("Scanned PDF OCR complete: %d pages, %d chars", total_pages, len(combined))

    force_gc()
    log_memory_usage("ocr_done", mem_before)
    return combined
