import logging
import re
from typing import Any

import numpy as np

from evaluation.metrics.base import BaseMetric, MetricResult

logger = logging.getLogger(__name__)


_SENTENCE_SPLITTER = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLITTER.split(text) if s.strip()]


def _get_keywords(text: str) -> set[str]:
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will",
        "would", "could", "should", "may", "might", "shall", "can",
        "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "as", "into", "through", "during", "before", "after", "above",
        "below", "between", "out", "off", "over", "under", "again",
        "further", "then", "once", "here", "there", "when", "where",
        "why", "how", "all", "each", "every", "both", "few", "more",
        "most", "other", "some", "such", "no", "nor", "not", "only",
        "own", "same", "so", "than", "too", "very", "just", "because",
        "and", "but", "or", "if", "while", "that", "this", "these",
        "those", "it", "its", "what", "which", "who", "whom",
    }
    words = set(re.findall(r"\b[a-zA-Z][a-zA-Z0-9]{1,}\b", text.lower()))
    return words - stop_words


def _claim_supported(claim: str, chunk_texts: list[str], threshold: float = 0.3) -> bool:
    claim_keywords = _get_keywords(claim)
    if not claim_keywords:
        return True

    for chunk_text in chunk_texts:
        chunk_keywords = _get_keywords(chunk_text)
        if not chunk_keywords:
            continue
        overlap = claim_keywords & chunk_keywords
        if len(overlap) / len(claim_keywords) >= threshold:
            return True
    return False


def _get_chunk_texts(chunks: list[dict[str, Any]]) -> list[str]:
    return [c.get("text", "") for c in chunks if c.get("text")]


class Faithfulness(BaseMetric):
    name = "faithfulness"
    description = "Fraction of answer claims supported by retrieved context"

    def compute(
        self,
        answer: str,
        chunks: list[dict[str, Any]],
    ) -> MetricResult:
        if not answer:
            return MetricResult(name=self.name, value=1.0, details={"total_claims": 0, "supported_claims": 0})

        chunk_texts = _get_chunk_texts(chunks)
        if not chunk_texts:
            return MetricResult(
                name=self.name, value=0.0,
                details={"total_claims": 0, "supported_claims": 0, "reason": "No context available"},
            )

        claims = _split_sentences(answer)
        if not claims:
            claims = [answer]

        supported = sum(1 for c in claims if _claim_supported(c, chunk_texts))
        score = supported / len(claims)

        return MetricResult(
            name=self.name,
            value=round(score, 4),
            details={
                "total_claims": len(claims),
                "supported_claims": supported,
                "unsupported_claims": len(claims) - supported,
            },
        )


class AnswerRelevancy(BaseMetric):
    name = "answer_relevancy"
    description = "How relevant the answer is to the question"

    def compute(
        self,
        question: str,
        answer: str,
    ) -> MetricResult:
        if not question or not answer:
            return MetricResult(name=self.name, value=0.0, details={"reason": "Missing question or answer"})

        q_keywords = _get_keywords(question)
        a_keywords = _get_keywords(answer)

        if not q_keywords or not a_keywords:
            return MetricResult(
                name=self.name, value=0.5,
                details={"reason": "Insufficient keywords for comparison"},
            )

        overlap = q_keywords & a_keywords
        precision = len(overlap) / len(a_keywords) if a_keywords else 0
        recall = len(overlap) / len(q_keywords) if q_keywords else 0

        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return MetricResult(
            name=self.name,
            value=round(f1, 4),
            details={
                "question_keywords": len(q_keywords),
                "answer_keywords": len(a_keywords),
                "overlap_keywords": len(overlap),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
            },
        )


class ContextPrecision(BaseMetric):
    name = "context_precision"
    description = "Whether relevant chunks are ranked higher"

    def compute(
        self,
        chunks: list[dict[str, Any]],
        ground_truth: str,
        question: str,
    ) -> MetricResult:
        if not chunks:
            return MetricResult(name=self.name, value=0.0, details={"reason": "No chunks provided"})

        gt_keywords = _get_keywords(ground_truth)
        if not gt_keywords:
            return MetricResult(name=self.name, value=1.0, details={"reason": "No ground truth keywords"})

        relevances = []
        for chunk in chunks:
            chunk_text = chunk.get("text", "")
            chunk_keywords = _get_keywords(chunk_text)
            if not chunk_keywords:
                relevances.append(0)
                continue
            overlap = gt_keywords & chunk_keywords
            relevance = len(overlap) / len(gt_keywords) if gt_keywords else 0
            relevances.append(1 if relevance > 0.1 else 0)

        if not any(relevances):
            return MetricResult(name=self.name, value=0.0, details={"relevant_chunks": 0, "total_chunks": len(chunks)})

        ap = 0.0
        relevant_count = 0
        for k, rel in enumerate(relevances, 1):
            if rel:
                relevant_count += 1
                ap += relevant_count / k

        total_relevant = sum(relevances)
        ap = ap / total_relevant if total_relevant > 0 else 0.0

        return MetricResult(
            name=self.name,
            value=round(ap, 4),
            details={
                "average_precision": round(ap, 4),
                "relevant_chunks": total_relevant,
                "total_chunks": len(chunks),
                "chunk_relevances": relevances,
            },
        )


class ContextRecall(BaseMetric):
    name = "context_recall"
    description = "Fraction of relevant chunks successfully retrieved"

    def compute(
        self,
        chunks: list[dict[str, Any]],
        ground_truth: str,
        question: str,
        total_expected_chunks: int = 5,
    ) -> MetricResult:
        if not chunks:
            return MetricResult(name=self.name, value=0.0, details={"reason": "No chunks retrieved"})

        gt_keywords = _get_keywords(ground_truth)
        if not gt_keywords:
            return MetricResult(name=self.name, value=1.0, details={"reason": "No ground truth keywords"})

        retrieved_relevant = 0
        for chunk in chunks:
            chunk_text = chunk.get("text", "")
            chunk_keywords = _get_keywords(chunk_text)
            if not chunk_keywords:
                continue
            overlap = gt_keywords & chunk_keywords
            if overlap:
                retrieved_relevant += 1

        recall = retrieved_relevant / total_expected_chunks if total_expected_chunks > 0 else 0.0
        recall = min(recall, 1.0)

        return MetricResult(
            name=self.name,
            value=round(recall, 4),
            details={
                "retrieved_relevant": retrieved_relevant,
                "total_expected": total_expected_chunks,
                "total_retrieved": len(chunks),
            },
        )
