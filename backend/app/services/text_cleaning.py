import logging
import re
import unicodedata

# Separates pages in extracted text (a form feed). The chunker uses it to record which page a chunk starts on.
PAGE_BREAK = "\f"

logger = logging.getLogger(__name__)


def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def remove_extra_spaces(text: str) -> str:
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    return text


def remove_page_numbers(text: str) -> str:
    lines = text.splitlines()
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^\d+$", stripped):
            continue
        if re.match(r"^- ?\d+ ?-$", stripped):
            continue
        if re.match(r"^(page|pg|p)\.?\s*\d+(\s*of\s*\d+)?$", stripped, re.IGNORECASE):
            continue
        if re.match(r"^\d+\s*/\s*\d+$", stripped):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def remove_repeated_headers(text: str) -> str:
    lines = text.splitlines()
    if len(lines) < 6:
        return text
    potential = lines[0].strip()
    if potential and lines[3].strip() == potential:
        cleaned = [
            line for i, line in enumerate(lines)
            if not (i % 3 == 0 and line.strip() == potential)
        ]
        return "\n".join(cleaned)
    return text


def remove_repeated_footers(text: str) -> str:
    lines = text.splitlines()
    if len(lines) < 6:
        return text
    potential = lines[-1].strip()
    if potential and lines[-4].strip() == potential:
        cleaned = [
            line for i, line in enumerate(lines)
            if not ((len(lines) - i - 1) % 3 == 0 and line.strip() == potential)
        ]
        return "\n".join(cleaned)
    return text


def _clean_page(raw: str) -> str:
    text = normalize_unicode(raw)
    text = remove_extra_spaces(text)
    text = remove_page_numbers(text)
    text = remove_repeated_headers(text)
    text = remove_repeated_footers(text)
    return text.strip()


def clean_text(raw: str) -> str:
    # Clean page by page and keep PAGE_BREAK between pages: str.splitlines() (used by the helpers above)
    # treats a form feed as a line boundary and would silently delete the markers.
    text = PAGE_BREAK.join(_clean_page(page) for page in raw.split(PAGE_BREAK))
    logger.info("Text cleaning complete: %d characters", len(text))
    return text
