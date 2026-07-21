import logging
import re

logger = logging.getLogger(__name__)


def analyze_ocr_quality(text: str, total_pages: int, ocr_confidences: list[float] | None = None) -> dict:
    if not text or not text.strip():
        return {
            "quality": "very_poor",
            "confidence": 0.0,
            "extracted_chars": 0,
            "blank_pages": total_pages,
            "missing_chars_ratio": 1.0,
        }

    extracted_chars = len(text)
    avg_word_len = _average_word_length(text)
    char_diversity = _character_diversity(text)
    missing_chars_ratio = _estimate_missing_chars(text)
    blank_pages = _estimate_blank_pages(text, total_pages)
    avg_conf = _average_confidence(ocr_confidences, text)

    score = _compute_quality_score(avg_conf, extracted_chars, avg_word_len, char_diversity, missing_chars_ratio, blank_pages, total_pages)

    if score >= 90:
        quality = "excellent"
    elif score >= 70:
        quality = "good"
    elif score >= 50:
        quality = "fair"
    elif score >= 30:
        quality = "poor"
    else:
        quality = "very_poor"

    logger.info(
        "OCR quality: %s (score=%.1f, chars=%d, blank=%d/%d, avg_conf=%.2f)",
        quality, score, extracted_chars, blank_pages, total_pages, avg_conf,
    )

    return {
        "quality": quality,
        "confidence": round(score, 1),
        "extracted_chars": extracted_chars,
        "blank_pages": blank_pages,
        "missing_chars_ratio": round(missing_chars_ratio, 4),
        "avg_word_length": round(avg_word_len, 2),
        "char_diversity": round(char_diversity, 4),
    }


def _average_word_length(text: str) -> float:
    words = text.split()
    if not words:
        return 0.0
    return sum(len(w) for w in words) / len(words)


def _character_diversity(text: str) -> float:
    if not text:
        return 0.0
    chars = set(text.lower())
    return len(chars) / max(len(text), 1)


def _estimate_missing_chars(text: str) -> float:
    garbage_pattern = re.compile(r"[^a-zA-Z0-9\s.,!?;:'\"()\-]")
    garbage_chars = len(garbage_pattern.findall(text))
    return min(garbage_chars / max(len(text), 1), 1.0)


def _estimate_blank_pages(text: str, total_pages: int) -> int:
    if total_pages <= 1:
        return 0
    avg_chars_per_page = len(text) / total_pages
    if avg_chars_per_page < 10:
        return total_pages
    return 0


def _average_confidence(ocr_confidences: list[float] | None, text: str) -> float:
    if ocr_confidences and len(ocr_confidences) > 0:
        return sum(ocr_confidences) / len(ocr_confidences)
    if len(text) < 50:
        return 0.2
    return 0.85


def _compute_quality_score(
    avg_conf: float,
    extracted_chars: int,
    avg_word_len: float,
    char_diversity: float,
    missing_chars_ratio: float,
    blank_pages: int,
    total_pages: int,
) -> float:
    conf_score = avg_conf * 40
    length_score = min(extracted_chars / 5000, 1.0) * 20
    word_len_score = min(max(avg_word_len - 2, 0) / 5, 1.0) * 10
    diversity_score = min(char_diversity / 0.1, 1.0) * 10
    missing_penalty = (1 - missing_chars_ratio) * 10
    blank_penalty = max(1.0 - (blank_pages / max(total_pages, 1)), 0) * 10

    score = conf_score + length_score + word_len_score + diversity_score + missing_penalty + blank_penalty
    return min(max(score, 0), 100)
