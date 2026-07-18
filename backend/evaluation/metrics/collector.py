from typing import Any

from evaluation.metrics.base import MetricCollection, MetricResult
from evaluation.metrics.ragas_metrics import Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall
from evaluation.metrics.deepeval_metrics import Hallucination, Bias, Toxicity, Correctness
from evaluation.metrics.custom_metrics import (
    ConfidenceCalibration,
    CitationAccuracy,
    ContradictionDetectionRate,
    RetrySuccessRate,
    ClarificationRate,
    UnsupportedAnswerRate,
    LatencyMetric,
)


class MetricsCollector:
    def __init__(self) -> None:
        self.faithfulness = Faithfulness()
        self.answer_relevancy = AnswerRelevancy()
        self.context_precision = ContextPrecision()
        self.context_recall = ContextRecall()
        self.hallucination = Hallucination()
        self.bias = Bias()
        self.toxicity = Toxicity()
        self.correctness = Correctness()
        self.confidence_calibration = ConfidenceCalibration()
        self.citation_accuracy = CitationAccuracy()
        self.contradiction_detection = ContradictionDetectionRate()
        self.retry_success = RetrySuccessRate()
        self.clarification_rate = ClarificationRate()
        self.unsupported_answer = UnsupportedAnswerRate()
        self.latency = LatencyMetric()

    def compute_single(
        self,
        question: str,
        answer: str,
        chunks: list[dict[str, Any]],
        ground_truth: str,
        citations: list[dict[str, Any]] | None = None,
        confidence_score: float | None = None,
        latencies: dict[str, float] | None = None,
    ) -> MetricCollection:
        collection = MetricCollection()

        collection.add(self.faithfulness(answer=answer, chunks=chunks))
        collection.add(self.answer_relevancy(question=question, answer=answer))
        collection.add(self.context_precision(chunks=chunks, ground_truth=ground_truth, question=question))
        collection.add(self.context_recall(chunks=chunks, ground_truth=ground_truth, question=question))
        collection.add(self.hallucination(answer=answer, chunks=chunks))
        collection.add(self.bias(answer=answer))
        collection.add(self.toxicity(answer=answer))
        collection.add(self.correctness(answer=answer, ground_truth=ground_truth))
        collection.add(self.unsupported_answer(answer=answer, chunks=chunks))

        if citations is not None:
            collection.add(self.citation_accuracy(citations=citations, chunks=chunks))

        if latencies is not None:
            total = latencies.get("total") or sum(v for v in latencies.values() if isinstance(v, (int, float)))
            collection.add(self.latency(latencies_ms=[total]))

        return collection

    def compute_aggregate(
        self,
        all_questions: list[dict[str, Any]],
        all_answers: list[str],
        all_chunks: list[list[dict[str, Any]]],
        all_ground_truths: list[str],
        all_citations: list[list[dict[str, Any]]],
        all_confidence_scores: list[float],
        all_latencies: list[dict[str, float]],
        all_contradictions_exist: list[bool],
        all_contradictions_detected: list[bool],
        all_clarifications_needed: list[bool],
        all_clarifications_triggered: list[bool],
        confidence_before_retry: list[float] | None = None,
        confidence_after_retry: list[float] | None = None,
    ) -> MetricCollection:
        collection = MetricCollection()

        faithfulness_scores = []
        relevancy_scores = []
        precision_scores = []
        recall_scores = []
        hallucination_scores = []
        bias_scores = []
        toxicity_scores = []
        correctness_scores = []
        unsupported_scores = []
        latencies_list = []
        calibration_confs = []
        calibration_correct = []

        for i, question in enumerate(all_questions):
            answer = all_answers[i]
            chunks = all_chunks[i]
            ground_truth = all_ground_truths[i]
            citations = all_citations[i]
            confidence = all_confidence_scores[i]
            latency = all_latencies[i]

            single = self.compute_single(
                question=question.get("question", ""),
                answer=answer,
                chunks=chunks,
                ground_truth=ground_truth,
                citations=citations,
                latencies=latency,
            )

            faithfulness_scores.append(single.get("faithfulness").value if single.get("faithfulness") else 0.0)
            relevancy_scores.append(single.get("answer_relevancy").value if single.get("answer_relevancy") else 0.0)
            precision_scores.append(single.get("context_precision").value if single.get("context_precision") else 0.0)
            recall_scores.append(single.get("context_recall").value if single.get("context_recall") else 0.0)
            hallucination_scores.append(single.get("hallucination").value if single.get("hallucination") else 0.0)
            bias_scores.append(single.get("bias").value if single.get("bias") else 1.0)
            toxicity_scores.append(single.get("toxicity").value if single.get("toxicity") else 1.0)
            correctness_scores.append(single.get("correctness").value if single.get("correctness") else 0.0)
            unsupported_scores.append(single.get("unsupported_answer_rate").value if single.get("unsupported_answer_rate") else 0.0)

            total_latency = latency.get("total", 0) if latency else 0
            if isinstance(total_latency, (int, float)):
                latencies_list.append(float(total_latency))

            calibration_confs.append(confidence)
            correct = correctness_scores[-1] >= 0.5 if correctness_scores else False
            calibration_correct.append(correct)

        collection.add(MetricResult(name="avg_faithfulness", value=round(sum(faithfulness_scores) / len(faithfulness_scores), 4) if faithfulness_scores else 0.0))
        collection.add(MetricResult(name="avg_answer_relevancy", value=round(sum(relevancy_scores) / len(relevancy_scores), 4) if relevancy_scores else 0.0))
        collection.add(MetricResult(name="avg_context_precision", value=round(sum(precision_scores) / len(precision_scores), 4) if precision_scores else 0.0))
        collection.add(MetricResult(name="avg_context_recall", value=round(sum(recall_scores) / len(recall_scores), 4) if recall_scores else 0.0))
        collection.add(MetricResult(name="avg_hallucination", value=round(sum(hallucination_scores) / len(hallucination_scores), 4) if hallucination_scores else 0.0))
        collection.add(MetricResult(name="avg_bias", value=round(sum(bias_scores) / len(bias_scores), 4) if bias_scores else 1.0))
        collection.add(MetricResult(name="avg_toxicity", value=round(sum(toxicity_scores) / len(toxicity_scores), 4) if toxicity_scores else 1.0))
        collection.add(MetricResult(name="avg_correctness", value=round(sum(correctness_scores) / len(correctness_scores), 4) if correctness_scores else 0.0))
        collection.add(MetricResult(name="avg_unsupported_answer_rate", value=round(sum(unsupported_scores) / len(unsupported_scores), 4) if unsupported_scores else 0.0))

        collection.add(self.latency(latencies_ms=latencies_list))
        collection.add(self.confidence_calibration(confidence_scores=calibration_confs, correctness_flags=calibration_correct))
        collection.add(self.contradiction_detection(contradictions_exist=all_contradictions_exist, contradictions_detected=all_contradictions_detected))
        collection.add(self.clarification_rate(clarification_needed=all_clarifications_needed, clarification_triggered=all_clarifications_triggered))

        if confidence_before_retry is not None and confidence_after_retry is not None:
            collection.add(self.retry_success(confidence_before=confidence_before_retry, confidence_after=confidence_after_retry))

        return collection
