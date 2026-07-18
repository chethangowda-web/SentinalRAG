import logging
import re

from app.core.config import settings

logger = logging.getLogger(__name__)


class TextChunk:
    def __init__(
        self,
        text: str,
        chunk_index: int,
        char_start: int,
        char_end: int,
        word_count: int,
        page_number: int | None = None,
    ):
        self.text = text
        self.chunk_index = chunk_index
        self.char_start = char_start
        self.char_end = char_end
        self.word_count = word_count
        self.page_number = page_number


def split_into_paragraphs(text: str) -> list[str]:
    raw = re.split(r"\n\s*\n", text)
    return [p.strip() for p in raw if p.strip()]


def _split_long_paragraph(para: str, chunk_size: int) -> list[str]:
    words = para.split()
    if len(words) <= chunk_size:
        return [para]
    parts: list[str] = []
    for i in range(0, len(words), chunk_size):
        part = " ".join(words[i : i + chunk_size])
        parts.append(part)
    return parts


def _finalize_chunk(
    parts: list[str],
    char_start: int,
    chunk_index: int,
    chunks: list[TextChunk],
) -> tuple[list[str], int, int]:
    chunk_text_str = "\n\n".join(parts)
    chunk_char_start = char_start
    chunk_char_end = chunk_char_start + len(chunk_text_str)
    word_count = len(chunk_text_str.split())

    chunks.append(TextChunk(
        text=chunk_text_str,
        chunk_index=chunk_index,
        char_start=chunk_char_start,
        char_end=chunk_char_end,
        word_count=word_count,
    ))

    return [], 0, chunk_char_end


def _finalize_with_overlap(
    parts: list[str],
    char_start: int,
    chunk_index: int,
    chunks: list[TextChunk],
) -> tuple[list[str], int, int]:
    chunk_text_str = "\n\n".join(parts)
    chunk_char_start = char_start
    chunk_char_end = chunk_char_start + len(chunk_text_str)
    word_count = len(chunk_text_str.split())

    chunks.append(TextChunk(
        text=chunk_text_str,
        chunk_index=chunk_index,
        char_start=chunk_char_start,
        char_end=chunk_char_end,
        word_count=word_count,
    ))

    overlap_text = _build_overlap(parts, settings.CHUNK_OVERLAP)
    if overlap_text:
        return [overlap_text], len(overlap_text.split()), chunk_char_end - len(overlap_text)
    return [], 0, chunk_char_end


def chunk_text(text: str) -> list[TextChunk]:
    paragraphs = split_into_paragraphs(text)
    chunks: list[TextChunk] = []
    current_parts: list[str] = []
    current_words = 0
    current_char_start = 0
    chunk_index = 0

    for para in paragraphs:
        para_words = len(para.split())

        if current_words + para_words <= settings.CHUNK_SIZE:
            current_parts.append(para)
            current_words += para_words
            continue

        if current_parts:
            current_parts, current_words, current_char_start = _finalize_with_overlap(
                current_parts, current_char_start, chunk_index, chunks,
            )
            chunk_index += 1

        sub_parts = _split_long_paragraph(para, settings.CHUNK_SIZE)
        for sub in sub_parts:
            sub_words = len(sub.split())
            if current_words + sub_words <= settings.CHUNK_SIZE:
                current_parts.append(sub)
                current_words += sub_words
            else:
                if current_parts:
                    current_parts, current_words, current_char_start = _finalize_chunk(
                        current_parts, current_char_start, chunk_index, chunks,
                    )
                    chunk_index += 1
                current_parts.append(sub)
                current_words += sub_words

    if current_parts:
        _finalize_chunk(current_parts, current_char_start, chunk_index, chunks)

    logger.info("Chunking complete: %d chunks from %d chars", len(chunks), len(text))
    for c in chunks:
        logger.debug("  Chunk %d: %d words, chars [%d:%d]", c.chunk_index, c.word_count, c.char_start, c.char_end)

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
