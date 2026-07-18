import logging
import re
from typing import Any

from evaluation.metrics.base import BaseMetric, MetricResult
from evaluation.metrics.ragas_metrics import _get_keywords, _split_sentences, _get_chunk_texts, _claim_supported

logger = logging.getLogger(__name__)


class ConfidenceCalibration(BaseMetric):
    name = "confidence_calibration"
    description = "Brier score between confidence scores and actual correctness"

    def compute(
        self,
        confidence_scores: list[float],
        correctness_flags: list[bool],
    ) -> MetricResult:
        if not confidence_scores or not correctness_flags:
            return MetricResult(
                name=self.name, value=0.0,
                details={"reason": "Empty inputs", "samples": 0},
            )

        if len(confidence_scores) != len(correctness_flags):
            return MetricResult(
                name=self.name, value=0.0,
                details={"reason": "Mismatched input lengths"},
            )

        n = len(confidence_scores)
        brier = 0.0
        for conf, correct in zip(confidence_scores, correctness_flags):
            prob = conf / 100.0
            true_val = 1.0 if correct else 0.0
            brier += (prob - true_val) ** 2

        brier /= n

        ece = 0.0
        n_bins = 10
        bin_edges = [i / n_bins for i in range(n_bins + 1)]
        for i in range(n_bins):
            lo, hi = bin_edges[i], bin_edges[i + 1]
            bin_confs = []
            bin_correct = []
            for conf, correct in zip(confidence_scores, correctness_flags):
                prob = conf / 100.0
                if lo <= prob < hi or (i == n_bins - 1 and prob == hi):
                    bin_confs.append(prob)
                    bin_correct.append(1.0 if correct else 0.0)
            if bin_confs:
                avg_conf = sum(bin_confs) / len(bin_confs)
                avg_correct = sum(bin_correct) / len(bin_correct)
                ece += abs(avg_conf - avg_correct) * (len(bin_confs) / n)

        return MetricResult(
            name=self.name,
            value=round(1.0 - brier, 4),
            details={
                "brier_score": round(brier, 4),
                "ece": round(ece, 4),
                "samples": n,
                "correct_count": sum(correctness_flags),
                "incorrect_count": n - sum(correctness_flags),
            },
        )


class CitationAccuracy(BaseMetric):
    name = "citation_accuracy"
    description = "Fraction of citations that correctly map to retrieved chunks"

    def compute(
        self,
        citations: list[dict[str, Any]],
        chunks: list[dict[str, Any]],
    ) -> MetricResult:
        if not citations:
            return MetricResult(name=self.name, value=1.0, details={"total_citations": 0})

        chunk_ids = {c.get("chunk_id") for c in chunks if c.get("chunk_id")}
        chunk_texts = {c.get("chunk_id", ""): c.get("text", "") for c in chunks if c.get("chunk_id")}

        accurate = 0
        citation_details = []

        for cit in citations:
            cid = cit.get("chunk_id", "")
            cit_text = cit.get("text", "")

            if cid in chunk_ids:
                accurate += 1
                citation_details.append({
                    "chunk_id": cid,
                    "accurate": True,
                    "reason": "chunk_id matched",
                })
            elif cit_text:
                matched = False
                for cid2, ctext in chunk_texts.items():
                    if cit_text[:100] in ctext or ctext[:100] in cit_text:
                        matched = True
                        break
                if matched:
                    accurate += 1
                    citation_details.append({
                        "chunk_id": cid,
                        "accurate": True,
                        "reason": "text matched",
                    })
                else:
                    citation_details.append({
                        "chunk_id": cid,
                        "accurate": False,
                        "reason": "no matching chunk found",
                    })
            else:
                citation_details.append({
                    "chunk_id": cid,
                    "accurate": False,
                    "reason": "no chunk_id or text to match",
                })

        score = accurate / len(citations) if citations else 1.0

        return MetricResult(
            name=self.name,
            value=round(score, 4),
            details={
                "accurate_citations": accurate,
                "total_citations": len(citations),
                "citation_details": citation_details,
            },
        )


class ContradictionDetectionRate(BaseMetric):
    name = "contradiction_detection_rate"
    description = "How often contradictions are correctly detected when they exist"

    def compute(
        self,
        contradictions_exist: list[bool],
        contradictions_detected: list[bool],
    ) -> MetricResult:
        if not contradictions_exist:
            return MetricResult(
                name=self.name, value=1.0,
                details={"reason": "No contradiction questions", "total": 0},
            )

        tp = 0
        fp = 0
        fn = 0
        tn = 0

        for exist, detected in zip(contradictions_exist, contradictions_detected):
            if exist and detected:
                tp += 1
            elif exist and not detected:
                fn += 1
            elif not exist and detected:
                fp += 1
            else:
                tn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return MetricResult(
            name=self.name,
            value=round(recall, 4),
            details={
                "true_positives": tp,
                "false_positives": fp,
                "false_negatives": fn,
                "true_negatives": tn,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
            },
        )


class RetrySuccessRate(BaseMetric):
    name = "retry_success_rate"
    description = "How often retry improves confidence score"

    def compute(
        self,
        confidence_before: list[float],
        confidence_after: list[float],
    ) -> MetricResult:
        if not confidence_before:
            return MetricResult(name=self.name, value=1.0, details={"reason": "No retries", "total": 0})

        improved = sum(
            1 for b, a in zip(confidence_before, confidence_after) if a > b
        )
        total = len(confidence_before)
        rate = improved / total if total > 0 else 0.0

        avg_improvement = 0.0
        if total > 0:
            deltas = [a - b for b, a in zip(confidence_before, confidence_after)]
            avg_improvement = sum(deltas) / total

        return MetricResult(
            name=self.name,
            value=round(rate, 4),
            details={
                "improved": improved,
                "no_improvement": total - improved,
                "total": total,
                "avg_improvement": round(avg_improvement, 2),
                "confidence_before": [round(b, 1) for b in confidence_before],
                "confidence_after": [round(a, 1) for a in confidence_after],
            },
        )


class ClarificationRate(BaseMetric):
    name = "clarification_rate"
    description = "How often clarification is correctly triggered for ambiguous questions"

    def compute(
        self,
        clarification_needed: list[bool],
        clarification_triggered: list[bool],
    ) -> MetricResult:
        if not clarification_needed:
            return MetricResult(
                name=self.name, value=1.0,
                details={"reason": "No clarification questions", "total": 0},
            )

        tp = 0
        fp = 0
        fn = 0
        tn = 0

        for needed, triggered in zip(clarification_needed, clarification_triggered):
            if needed and triggered:
                tp += 1
            elif needed and not triggered:
                fn += 1
            elif not needed and triggered:
                fp += 1
            else:
                tn += 1

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return MetricResult(
            name=self.name,
            value=round(recall, 4),
            details={
                "true_positives": tp,
                "false_positives": fp,
                "false_negatives": fn,
                "true_negatives": tn,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
            },
        )


class UnsupportedAnswerRate(BaseMetric):
    name = "unsupported_answer_rate"
    description = "Fraction of answers with unsupported claims"

    def compute(
        self,
        answer: str,
        chunks: list[dict[str, Any]],
    ) -> MetricResult:
        if not answer:
            return MetricResult(name=self.name, value=0.0, details={"reason": "Empty answer"})

        chunk_texts = _get_chunk_texts(chunks)
        if not chunk_texts:
            return MetricResult(
                name=self.name, value=1.0,
                details={"reason": "No context", "unsupported": True},
            )

        claims = _split_sentences(answer)
        if not claims:
            claims = [answer]

        unsupported = [c for c in claims if not _claim_supported(c, chunk_texts, threshold=0.2)]
        rate = len(unsupported) / len(claims)

        return MetricResult(
            name=self.name,
            value=round(rate, 4),
            details={
                "total_claims": len(claims),
                "unsupported_claims": len(unsupported),
                "supported_claims": len(claims) - len(unsupported),
                "unsupported_examples": unsupported[:3],
            },
        )


class LatencyMetric(BaseMetric):
    name = "latency"
    description = "Average total latency in milliseconds"

    def compute(
        self,
        latencies_ms: list[float],
    ) -> MetricResult:
        if not latencies_ms:
            return MetricResult(name=self.name, value=0.0, details={"reason": "No latency data"})

        avg = sum(latencies_ms) / len(latencies_ms)
        p50 = sorted(latencies_ms)[len(latencies_ms) // 2]
        p95 = sorted(latencies_ms)[int(len(latencies_ms) * 0.95)]
        p99 = sorted(latencies_ms)[int(len(latencies_ms) * 0.99)]

        return MetricResult(
            name=self.name,
            value=round(avg, 1),
            details={
                "average_ms": round(avg, 1),
                "min_ms": round(min(latencies_ms), 1),
                "max_ms": round(max(latencies_ms), 1),
                "p50_ms": round(p50, 1),
                "p95_ms": round(p95, 1),
                "p99_ms": round(p99, 1),
                "samples": len(latencies_ms),
            },
        )
