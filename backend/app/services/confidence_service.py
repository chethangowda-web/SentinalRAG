import logging
import time
from typing import Literal

logger = logging.getLogger(__name__)

ConfidenceLevel = Literal["HIGH", "MEDIUM", "LOW"]


class ConfidenceResult:
    def __init__(self, score: float, level: ConfidenceLevel):
        self.score = score
        self.level = level


def _compute_weighted_confidence(
    vector_scores: list[float],
    rerank_scores: list[float],
    total_results: int,
    citation_count: int = 0,
) -> tuple[float, float, float, float, float]:
    weights = [1.0, 0.6, 0.4, 0.25, 0.15]

    weighted_vec_sum = 0.0
    weighted_rerank_sum = 0.0
    weight_sum = 0.0

    for rank, (vec, rerank) in enumerate(zip(vector_scores, rerank_scores)):
        w = weights[rank] if rank < len(weights) else weights[-1]
        weighted_vec_sum += w * max(vec, 0.0)
        weighted_rerank_sum += w * max(rerank, 0.0)
        weight_sum += w

    if weight_sum == 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0

    avg_vector = weighted_vec_sum / weight_sum
    avg_rerank = weighted_rerank_sum / weight_sum

    coverage = min(total_results / 5.0, 1.0)
    citation_factor = min(citation_count / 5.0, 1.0)

    vector_contrib = avg_vector * 0.30
    rerank_contrib = avg_rerank * 0.50
    coverage_contrib = coverage * 0.20

    raw_score = vector_contrib + rerank_contrib + coverage_contrib
    score = min(max(raw_score, 0.0), 1.0)

    return score, avg_vector, avg_rerank, coverage, citation_factor


def calculate_confidence(
    vector_scores: list[float],
    rerank_scores: list[float],
    total_results: int,
) -> ConfidenceResult:
    start = time.perf_counter()

    if total_results == 0 or not vector_scores:
        logger.info("Confidence: 0.0 -> LOW (no results)")
        return ConfidenceResult(score=0.0, level="LOW")

    score, avg_vector, avg_rerank, coverage, _ = _compute_weighted_confidence(
        vector_scores, rerank_scores, total_results,
    )

    score_pct = round(score * 100, 1)

    if score_pct >= 80.0:
        level: ConfidenceLevel = "HIGH"
    elif score_pct >= 50.0:
        level = "MEDIUM"
    else:
        level = "LOW"

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        "Confidence: %.1f -> %s (w_vec=%.4f w_rerank=%.4f coverage=%.2f) in %.1fms",
        score_pct, level, avg_vector, avg_rerank, coverage, elapsed,
    )

    return ConfidenceResult(score=score_pct, level=level)


def calculate_confidence_with_breakdown(
    vector_scores: list[float],
    rerank_scores: list[float],
    total_results: int,
    citation_count: int = 0,
    contradiction_detected: bool = False,
    retry_success: bool = False,
) -> tuple[ConfidenceResult, dict]:
    if total_results == 0 or not vector_scores:
        return ConfidenceResult(score=0.0, level="LOW"), {
            "vector_similarity": 0.0, "vector_contribution": 0.0,
            "coverage": 0.0, "coverage_contribution": 0.0,
            "cross_encoder_score": 0.0, "cross_encoder_contribution": 0.0,
            "citation_count": 0, "citation_contribution": 0.0,
            "contradiction_status": "none", "retry_success": False,
            "raw_score": 0.0, "final_score": 0.0,
        }

    score, avg_vector, avg_rerank, coverage, citation_factor = _compute_weighted_confidence(
        vector_scores, rerank_scores, total_results, citation_count,
    )

    vector_contrib = round(avg_vector * 0.30 * 100, 2)
    rerank_contrib = round(avg_rerank * 0.50 * 100, 2)
    coverage_contrib = round(coverage * 0.20 * 100, 2)
    citation_contrib = round(citation_factor * 0.0, 2)

    score_pct = round(score * 100, 1)
    score_clamped = min(max(score_pct, 0.0), 100.0)

    contradiction_status = "detected" if contradiction_detected else "none"

    if score_clamped >= 80.0:
        level: ConfidenceLevel = "HIGH"
    elif score_clamped >= 50.0:
        level = "MEDIUM"
    else:
        level = "LOW"

    breakdown = {
        "vector_similarity": round(avg_vector, 4),
        "vector_contribution": vector_contrib,
        "coverage": round(coverage, 4),
        "coverage_contribution": coverage_contrib,
        "cross_encoder_score": round(avg_rerank, 4),
        "cross_encoder_contribution": rerank_contrib,
        "citation_count": citation_count,
        "citation_contribution": citation_contrib,
        "contradiction_status": contradiction_status,
        "retry_success": retry_success,
        "raw_score": round(score, 4),
        "final_score": score_clamped,
    }

    return ConfidenceResult(score=score_clamped, level=level), breakdown
