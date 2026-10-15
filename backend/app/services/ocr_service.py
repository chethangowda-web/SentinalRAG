import gc
import io
import logging
import os
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import InvalidUploadError
from app.utils.memory import force_gc, log_memory_usage

# Tesseract spawns one thread per core by default, and each thread holds working memory.
# One thread is plenty for a single page and keeps the peak small on a memory-limited host.
os.environ.setdefault("OMP_THREAD_LIMIT", "1")

# Images are shrunk to this longest side before OCR: text stays legible, memory stays bounded.
MAX_OCR_SIDE = 2500
# Refuse images that would need an unreasonable amount of memory just to decode.
MAX_IMAGE_PIXELS = 50_000_000
OCR_TIMEOUT_SECONDS = 120

logger = logging.getLogger(__name__)

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import pytesseract
except Exception:
    pytesseract = None

TESSERACT_AVAILABLE = Image is not None and pytesseract is not None
if not TESSERACT_AVAILABLE:
    logger.warning("pytesseract or Pillow not available — OCR unavailable")


try:
    import fitz

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not installed")


def prepare_for_ocr(image: "Image.Image") -> "Image.Image":
    """Grayscale the image and shrink it so its longest side is at most MAX_OCR_SIDE.

    Raises InvalidUploadError for images too large to process safely. Reading the size does not
    decode the pixels, so the check itself is cheap.
    """
    width, height = image.size
    if width * height > MAX_IMAGE_PIXELS:
        raise InvalidUploadError(
            detail=f"Image is too large ({width}x{height}). Please upload one under {MAX_IMAGE_PIXELS // 1_000_000} megapixels."
        )
    scale = MAX_OCR_SIDE / max(width, height)
    if scale < 1:
        image = image.resize((max(1, int(width * scale)), max(1, int(height * scale))), Image.Resampling.LANCZOS)
    return image.convert("L")


def ocr_image(image_path: Path | bytes) -> str:
    if not TESSERACT_AVAILABLE:
        raise RuntimeError("OCR is not available — pytesseract/Pillow not installed")

    if isinstance(image_path, bytes):
        image = Image.open(io.BytesIO(image_path))
    else:
        image = Image.open(image_path)
    try:
        prepared = prepare_for_ocr(image)
        try:
            text = pytesseract.image_to_string(prepared, lang=settings.OCR_LANGUAGE, timeout=OCR_TIMEOUT_SECONDS)
        finally:
            prepared.close()
    finally:
        image.close()
        gc.collect()
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
