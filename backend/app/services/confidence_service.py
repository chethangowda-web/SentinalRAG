import logging
import time
from typing import Literal

logger = logging.getLogger(__name__)

ConfidenceLevel = Literal["HIGH", "MEDIUM", "LOW"]


class ConfidenceResult:
    def __init__(self, score: float, level: ConfidenceLevel):
        self.score = score
        self.level = level


def calculate_confidence(
    vector_scores: list[float],
    rerank_scores: list[float],
    total_results: int,
) -> ConfidenceResult:
    start = time.perf_counter()

    if total_results == 0:
        logger.info("Confidence: 0.0 -> LOW (no results)")
        return ConfidenceResult(score=0.0, level="LOW")

    avg_vector = sum(vector_scores) / len(vector_scores) if vector_scores else 0.0
    avg_rerank = sum(rerank_scores) / len(rerank_scores) if rerank_scores else 0.0
    coverage = min(total_results / 10.0, 1.0)

    vector_norm = avg_vector
    rerank_norm = avg_rerank

    raw_score = (
        vector_norm * 0.30 +
        rerank_norm * 0.50 +
        coverage * 0.20
    )

    score = round(raw_score * 100, 1)
    score = min(max(score, 0.0), 100.0)

    if score >= 80.0:
        level: ConfidenceLevel = "HIGH"
    elif score >= 50.0:
        level = "MEDIUM"
    else:
        level = "LOW"

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        "Confidence: %.1f -> %s (avg_vec=%.4f avg_rerank=%.4f coverage=%.2f) in %.1fms",
        score, level, avg_vector, avg_rerank, coverage, elapsed,
    )

    return ConfidenceResult(score=score, level=level)


def calculate_confidence_with_breakdown(
    vector_scores: list[float],
    rerank_scores: list[float],
    total_results: int,
    citation_count: int = 0,
    contradiction_detected: bool = False,
    retry_success: bool = False,
) -> tuple[ConfidenceResult, dict]:
    if total_results == 0:
        return ConfidenceResult(score=0.0, level="LOW"), {
            "vector_similarity": 0.0, "vector_contribution": 0.0,
            "coverage": 0.0, "coverage_contribution": 0.0,
            "cross_encoder_score": 0.0, "cross_encoder_contribution": 0.0,
            "citation_count": 0, "citation_contribution": 0.0,
            "contradiction_status": "none", "retry_success": False,
            "raw_score": 0.0, "final_score": 0.0,
        }

    avg_vector = sum(vector_scores) / len(vector_scores) if vector_scores else 0.0
    avg_rerank = sum(rerank_scores) / len(rerank_scores) if rerank_scores else 0.0
    coverage = min(total_results / 10.0, 1.0)
    citation_factor = min(citation_count / 5.0, 1.0)

    vector_norm = avg_vector
    rerank_norm = avg_rerank

    vector_contrib = vector_norm * 0.30 * 100
    rerank_contrib = rerank_norm * 0.50 * 100
    coverage_contrib = coverage * 0.20 * 100
    citation_contrib = citation_factor * 0.0

    raw_score = vector_norm * 0.30 + rerank_norm * 0.50 + coverage * 0.20
    score = round(raw_score * 100, 1)
    score = min(max(score, 0.0), 100.0)

    contradiction_status = "detected" if contradiction_detected else "none"

    if score >= 80.0:
        level: ConfidenceLevel = "HIGH"
    elif score >= 50.0:
        level = "MEDIUM"
    else:
        level = "LOW"

    breakdown = {
        "vector_similarity": round(avg_vector, 4),
        "vector_contribution": round(vector_contrib, 2),
        "coverage": round(coverage, 4),
        "coverage_contribution": round(coverage_contrib, 2),
        "cross_encoder_score": round(avg_rerank, 4),
        "cross_encoder_contribution": round(rerank_contrib, 2),
        "citation_count": citation_count,
        "citation_contribution": round(citation_contrib, 2),
        "contradiction_status": contradiction_status,
        "retry_success": retry_success,
        "raw_score": round(raw_score, 4),
        "final_score": score,
    }

    return ConfidenceResult(score=score, level=level), breakdown
