import logging
import re
import uuid

from app.core.config import settings
from app.services.text_cleaning import PAGE_BREAK

logger = logging.getLogger(__name__)

_SECTION_HEADER_RE = re.compile(
    r"^(#{1,3}\s+|(?:[A-Z][A-Za-z\s]{2,50}):\s*$|(?:Chapter|Section|Part|Appendix)\s+\d+|^\d+\.\s+[A-Z])",
)
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


class TextChunk:
    def __init__(
        self,
        chunk_id: str,
        text: str,
        chunk_index: int,
        char_start: int,
        char_end: int,
        word_count: int,
        page_number: int | None = None,
        section: str | None = None,
    ):
        self.chunk_id = chunk_id
        self.text = text
        self.chunk_index = chunk_index
        self.char_start = char_start
        self.char_end = char_end
        self.word_count = word_count
        self.page_number = page_number
        self.section = section


def split_into_paragraphs(text: str) -> list[str]:
    raw = re.split(r"\n\s*\n", text)
    return [p.strip() for p in raw if p.strip()]


def _detect_section(para: str) -> str | None:
    m = _SECTION_HEADER_RE.match(para.strip())
    if m:
        return para.strip()[:120]
    if len(para.split()) <= 8 and para.strip().endswith(":") and len(para.strip()) > 3:
        return para.strip()[:120]
    return None


def _split_long_paragraph(para: str, chunk_size: int) -> list[str]:
    words = para.split()
    if len(words) <= chunk_size:
        return [para]
    sentences = _SENTENCE_BOUNDARY.split(para)
    parts: list[str] = []
    current: list[str] = []
    current_len = 0
    for sent in sentences:
        sent_len = len(sent.split())
        if current_len + sent_len <= chunk_size:
            current.append(sent)
            current_len += sent_len
        else:
            if current:
                parts.append(" ".join(current))
            if sent_len > chunk_size:
                sub_words = sent.split()
                for i in range(0, len(sub_words), chunk_size):
                    parts.append(" ".join(sub_words[i:i + chunk_size]))
                current = []
                current_len = 0
            else:
                current = [sent]
                current_len = sent_len
    if current:
        parts.append(" ".join(current))
    return parts


def _finalize_chunk(
    parts: list[str],
    char_start: int,
    chunk_index: int,
    chunks: list[TextChunk],
    section: str | None = None,
    page_number: int | None = None,
) -> tuple[list[str], int, int]:
    chunk_text_str = "\n\n".join(parts)
    chunk_char_start = char_start
    chunk_char_end = chunk_char_start + len(chunk_text_str)
    word_count = len(chunk_text_str.split())

    chunks.append(TextChunk(
        chunk_id=str(uuid.uuid4()),
        text=chunk_text_str,
        chunk_index=chunk_index,
        char_start=chunk_char_start,
        char_end=chunk_char_end,
        word_count=word_count,
        page_number=page_number,
        section=section,
    ))

    return [], 0, chunk_char_end


def _finalize_with_overlap(
    parts: list[str],
    char_start: int,
    chunk_index: int,
    chunks: list[TextChunk],
    section: str | None = None,
    page_number: int | None = None,
) -> tuple[list[str], int, int]:
    chunk_text_str = "\n\n".join(parts)
    chunk_char_start = char_start
    chunk_char_end = chunk_char_start + len(chunk_text_str)
    word_count = len(chunk_text_str.split())

    chunks.append(TextChunk(
        chunk_id=str(uuid.uuid4()),
        text=chunk_text_str,
        chunk_index=chunk_index,
        char_start=chunk_char_start,
        char_end=chunk_char_end,
        word_count=word_count,
        page_number=page_number,
        section=section,
    ))

    overlap_text = _build_overlap(parts, settings.CHUNK_OVERLAP)
    if overlap_text:
        return [overlap_text], len(overlap_text.split()), chunk_char_end - len(overlap_text)
    return [], 0, chunk_char_end


def chunk_text(text: str, paginated: bool = False) -> list[TextChunk]:
    """Split text into overlapping chunks.

    Pages are separated by PAGE_BREAK in text extracted from PDFs/images. With `paginated` (or any
    page break present) each chunk records the page it starts on; otherwise page_number stays None.
    """
    pages = text.split(PAGE_BREAK)
    track_pages = paginated or len(pages) > 1
    paragraphs: list[str] = []
    paragraph_pages: list[int | None] = []
    for page_no, page_text in enumerate(pages, start=1):
        for paragraph in split_into_paragraphs(page_text):
            paragraphs.append(paragraph)
            paragraph_pages.append(page_no if track_pages else None)

    chunks: list[TextChunk] = []
    current_parts: list[str] = []
    current_words = 0
    current_char_start = 0
    chunk_index = 0
    current_section: str | None = None
    # Page of the first *new* paragraph in the chunk being built. Overlap text carried over from the
    # previous chunk does not count: a chunk is cited by the page of its own content.
    current_page: int | None = None
    # False while the chunk being built holds only overlap carried over from the previous chunk.
    # Such a chunk adds nothing new (it would be a duplicate of the previous chunk's tail), so it is dropped.
    has_new = False

    def add(part: str, words: int, page: int | None) -> None:
        nonlocal current_words, current_page, has_new
        if current_page is None:
            current_page = page
        current_parts.append(part)
        current_words += words
        has_new = True

    for para, page in zip(paragraphs, paragraph_pages):
        detected = _detect_section(para)

        if detected:
            if current_parts and has_new:
                current_parts, current_words, current_char_start = _finalize_with_overlap(
                    current_parts, current_char_start, chunk_index, chunks,
                    section=current_section, page_number=current_page,
                )
                current_page = None
                has_new = False
                chunk_index += 1
            current_section = detected

            if len(para.split()) <= 8:
                continue

        para_words = len(para.split())

        if current_words + para_words <= settings.CHUNK_SIZE:
            add(para, para_words, page)
            continue

        if current_parts and has_new:
            current_parts, current_words, current_char_start = _finalize_with_overlap(
                current_parts, current_char_start, chunk_index, chunks,
                section=current_section, page_number=current_page,
            )
            current_page = None
            has_new = False
            chunk_index += 1
        elif current_parts:
            current_parts, current_words = [], 0  # overlap only: nothing new to keep

        sub_parts = _split_long_paragraph(para, settings.CHUNK_SIZE)
        for sub in sub_parts:
            sub_words = len(sub.split())
            if current_words + sub_words <= settings.CHUNK_SIZE:
                add(sub, sub_words, page)
            else:
                if current_parts and has_new:
                    current_parts, current_words, current_char_start = _finalize_chunk(
                        current_parts, current_char_start, chunk_index, chunks,
                        section=current_section, page_number=current_page,
                    )
                    current_page = None
                    has_new = False
                    chunk_index += 1
                add(sub, sub_words, page)

    if current_parts and has_new:
        _finalize_chunk(current_parts, current_char_start, chunk_index, chunks, section=current_section, page_number=current_page)

    logger.info("Chunking complete: %d chunks from %d chars", len(chunks), len(text))
    for c in chunks:
        logger.debug(
            "  Chunk %d: %d words, chars [%d:%d], section=%s, page=%s",
            c.chunk_index, c.word_count, c.char_start, c.char_end, c.section, c.page_number,
        )

    return chunks


def _build_overlap(parts: list[str], target_words: int) -> str:
    collected: list[str] = []
    word_count = 0
    for part in reversed(parts):
        p_words = part.split()
        if word_count + len(p_words) <= target_words:
            collected.insert(0, part)
            word_count += len(p_words)
        else:
            remaining = target_words - word_count
            if remaining > 0:
                collected.insert(0, " ".join(p_words[-remaining:]))
            break
    return "\n\n".join(collected)
