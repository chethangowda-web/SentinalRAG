import logging
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from PIL import Image

    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract or Pillow not installed — OCR unavailable")


try:
    import fitz

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not installed")


def ocr_image(image_path: Path) -> str:
    if not TESSERACT_AVAILABLE:
        raise RuntimeError("OCR is not available — pytesseract/Pillow not installed")

    image = Image.open(image_path)
    text = pytesseract.image_to_string(image, lang=settings.OCR_LANGUAGE)
    logger.info("OCR completed for %s (%d chars)", image_path, len(text))
    return text


def ocr_pdf(pdf_path: Path) -> str:
    if not PYMUPDF_AVAILABLE:
        raise RuntimeError("PyMuPDF is not available")

    if not TESSERACT_AVAILABLE:
        raise RuntimeError("OCR is not available — pytesseract/Pillow not installed")

    doc = fitz.open(str(pdf_path))
    total_pages = len(doc)
    all_text: list[str] = []

    logger.info("Starting OCR for scanned PDF: %s (%d pages)", pdf_path, total_pages)

    for page_num in range(total_pages):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=300)
        img_data = pix.tobytes("png")
        img_path = Path(pdf_path.parent, f"_ocr_temp_{page_num}.png")
        try:
            with open(img_path, "wb") as f:
                f.write(img_data)
            text = ocr_image(img_path)
            all_text.append(text)
        finally:
            if img_path.exists():
                img_path.unlink()

    doc.close()
    combined = "\n".join(all_text)
    logger.info("Scanned PDF OCR complete: %d pages, %d chars", total_pages, len(combined))
    return combined
