
from app.services.confidence_service import (
    calculate_confidence,
    calculate_confidence_with_breakdown,
)


class TestConfidenceBreakdown:
    def test_basic_breakdown_structure(self):
        vector_scores = [0.95, 0.92, 0.88]
        rerank_scores = [0.94, 0.91, 0.87]

        result, breakdown = calculate_confidence_with_breakdown(
            vector_scores=vector_scores,
            rerank_scores=rerank_scores,
            total_results=3,
        )

        assert breakdown["vector_similarity"] > 0
        assert breakdown["vector_contribution"] > 0
        assert breakdown["cross_encoder_score"] > 0
        assert breakdown["cross_encoder_contribution"] > 0
        assert breakdown["coverage"] > 0
        assert breakdown["coverage_contribution"] > 0
        assert breakdown["contradiction_status"] == "none"
        assert breakdown["retry_success"] is False
        assert breakdown["final_score"] == result.score
        assert breakdown["raw_score"] > 0

    def test_high_confidence_breakdown(self):
        vector_scores = [0.98, 0.97, 0.96, 0.95, 0.94]
        rerank_scores = [0.97, 0.96, 0.95, 0.94, 0.93]

        result, breakdown = calculate_confidence_with_breakdown(
            vector_scores=vector_scores,
            rerank_scores=rerank_scores,
            total_results=5,
        )

        assert result.level == "HIGH"
        assert result.score >= 80
        assert breakdown["final_score"] >= 80

    def test_low_confidence_breakdown_empty(self):
        result, breakdown = calculate_confidence_with_breakdown(
            vector_scores=[],
            rerank_scores=[],
            total_results=0,
        )

        assert result.level == "LOW"
        assert result.score == 0.0
        assert breakdown["final_score"] == 0.0
        assert breakdown["contradiction_status"] == "none"

    def test_contradiction_status_in_breakdown(self):
        vector_scores = [0.90, 0.85]
        rerank_scores = [0.88, 0.82]

        _, breakdown = calculate_confidence_with_breakdown(
            vector_scores=vector_scores,
            rerank_scores=rerank_scores,
            total_results=2,
            contradiction_detected=True,
        )

        assert breakdown["contradiction_status"] == "detected"

    def test_no_contradiction_in_breakdown(self):
        _, breakdown = calculate_confidence_with_breakdown(
            vector_scores=[0.9],
            rerank_scores=[0.85],
            total_results=1,
            contradiction_detected=False,
        )

        assert breakdown["contradiction_status"] == "none"

    def test_retry_success_in_breakdown(self):
        _, breakdown = calculate_confidence_with_breakdown(
            vector_scores=[0.9],
            rerank_scores=[0.85],
            total_results=1,
            retry_success=True,
        )

        assert breakdown["retry_success"] is True

    def test_citation_count_in_breakdown(self):
        _, breakdown = calculate_confidence_with_breakdown(
            vector_scores=[0.9, 0.8, 0.7, 0.6],
            rerank_scores=[0.85, 0.75, 0.65, 0.55],
            total_results=4,
            citation_count=4,
        )

        assert breakdown["citation_count"] == 4

    def test_breakdown_components_sum(self):
        vector_scores = [0.95, 0.90]
        rerank_scores = [0.92, 0.88]

        result, breakdown = calculate_confidence_with_breakdown(
            vector_scores=vector_scores,
            rerank_scores=rerank_scores,
            total_results=2,
        )

        vector_contrib = breakdown["vector_contribution"]
        rerank_contrib = breakdown["cross_encoder_contribution"]
        coverage_contrib = breakdown["coverage_contribution"]

        expected_score = vector_contrib + rerank_contrib + coverage_contrib
        assert abs(expected_score - breakdown["final_score"]) < 0.1

    def test_calculate_confidence_consistency(self):
        vector_scores = [0.95, 0.92, 0.88]
        rerank_scores = [0.94, 0.91, 0.87]

        simple = calculate_confidence(vector_scores, rerank_scores, 3)
        with_breakdown, breakdown = calculate_confidence_with_breakdown(
            vector_scores, rerank_scores, 3
        )

        assert simple.score == with_breakdown.score
        assert simple.level == with_breakdown.level
