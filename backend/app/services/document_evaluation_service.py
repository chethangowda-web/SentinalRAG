import asyncio
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document
from app.services.retrieval_service import retrieve
from app.services.answer_generator import generate_answer
from evaluation.metrics.collector import MetricsCollector

logger = logging.getLogger(__name__)


async def evaluate_document(document_id: str, db: AsyncSession, user_id: str | None = None) -> dict[str, Any]:
    start_time = time.perf_counter()

    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if document is None:
        raise ValueError(f"Document {document_id} not found")

    logger.info("Starting per-document evaluation for %s: %s", document_id, document.filename)

    questions = _generate_questions(document)

    metrics_collector = MetricsCollector()
    per_question: list[dict[str, Any]] = []
    all_latencies: list[float] = []
    all_confidences: list[float] = []

    for q in questions:
        pq_result = await _evaluate_single_question(q, document, db, metrics_collector)
        per_question.append(pq_result)
        total_ms = pq_result.get("latency_ms", 0)
        all_latencies.append(total_ms)
        all_confidences.append(pq_result.get("confidence_score", 0.0))

    document_text = document.text_content or ""
    doc_keywords = set(document.keywords.split(",")) if document.keywords else set()

    summary_metrics = _compute_summary_metrics(
        per_question, all_latencies, all_confidences, doc_keywords,
    )

    elapsed = round(time.perf_counter() - start_time, 2)

    return {
        "document_id": document_id,
        "filename": document.filename,
        "document_type": document.document_type,
        "document_summary": document.summary,
        "total_questions": len(questions),
        "evaluation_time_seconds": elapsed,
        "summary_metrics": summary_metrics,
        "per_question": per_question,
        "recommendations": _generate_recommendations(summary_metrics),
    }


def _generate_questions(document: Document) -> list[dict[str, str]]:
    questions: list[dict[str, str]] = []
    summary = document.summary or ""
    key_topics_str = document.key_topics or ""
    keywords_str = document.keywords or ""

    topics = [t.strip() for t in key_topics_str.split(",") if t.strip()] if key_topics_str else []
    keywords = [k.strip() for k in keywords_str.split(",") if k.strip()] if keywords_str else []

    if topics:
        for topic in topics[:4]:
            questions.append({
                "question": f"What does this document say about {topic}?",
                "type": "topic",
                "source": "key_topics",
            })

    if keywords:
        for kw in keywords[:4]:
            questions.append({
                "question": f"What information is provided about {kw} in this document?",
                "type": "keyword",
                "source": "keywords",
            })

    if summary:
        summary_sentences = [s.strip() for s in summary.split(".") if len(s.strip()) > 20]
        for sent in summary_sentences[:2]:
            questions.append({
                "question": f"Tell me more about: {sent.strip()}",
                "type": "summary_detail",
                "source": "summary",
            })

    doc_type = document.document_type or "document"
    questions.append({
        "question": f"What is the main purpose and key conclusions of this {doc_type}?",
        "type": "overall",
        "source": "general",
    })

    logger.info("Generated %d evaluation questions for document %s", len(questions), document.id)
    return questions


async def _evaluate_single_question(
    q: dict[str, str],
    document: Document,
    db: AsyncSession,
    metrics_collector: MetricsCollector,
) -> dict[str, Any]:
    question_text = q["question"]
    qid = str(uuid.uuid4())[:8]

    search_response = await retrieve(question_text, db, user_id=document.user_id)

    chunks = []
    for r in search_response.results:
        chunks.append({
            "chunk_id": r.chunk_id,
            "document_id": r.document_id,
            "text": r.text,
            "page_number": r.page_number,
            "section": r.section,
            "filename": r.filename,
            "vector_score": r.vector_score,
            "bm25_score": r.bm25_score,
            "rerank_score": r.rerank_score,
        })

    answer_text = generate_answer(question_text, chunks)

    metrics = metrics_collector.compute_single(
        question=question_text,
        answer=answer_text,
        chunks=chunks,
        ground_truth=document.text_content or "",
        citations=None,
        confidence_score=search_response.confidence,
        latencies=search_response.latencies,
    )

    total_latency = 0.0
    if search_response.latencies:
        total_latency = search_response.latencies.get("total", 0.0)

    return {
        "question_id": qid,
        "question": question_text,
        "question_type": q.get("type", "general"),
        "answer": answer_text,
        "confidence_score": search_response.confidence,
        "confidence_level": search_response.confidence_level,
        "latency_ms": total_latency,
        "num_chunks_retrieved": len(chunks),
        "metrics": {
            "faithfulness": _metric_value(metrics, "faithfulness"),
            "answer_relevancy": _metric_value(metrics, "answer_relevancy"),
            "hallucination": _metric_value(metrics, "hallucination"),
            "bias": _metric_value(metrics, "bias"),
            "toxicity": _metric_value(metrics, "toxicity"),
            "unsupported_answer_rate": _metric_value(metrics, "unsupported_answer_rate"),
        },
        "retrieved_chunks": [_chunk_summary(c) for c in chunks[:3]],
    }


def _compute_summary_metrics(
    per_question: list[dict[str, Any]],
    all_latencies: list[float],
    all_confidences: list[float],
    doc_keywords: set[str],
) -> dict[str, Any]:
    n = len(per_question)
    if n == 0:
        return {"error": "No questions evaluated"}

    faithfulness_vals = [pq["metrics"]["faithfulness"] for pq in per_question]
    relevancy_vals = [pq["metrics"]["answer_relevancy"] for pq in per_question]
    hallucination_vals = [pq["metrics"]["hallucination"] for pq in per_question]
    bias_vals = [pq["metrics"]["bias"] for pq in per_question]
    toxicity_vals = [pq["metrics"]["toxicity"] for pq in per_question]
    unsupported_vals = [pq["metrics"]["unsupported_answer_rate"] for pq in per_question]

    avg_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0
    avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0
    high_conf_count = sum(1 for c in all_confidences if c >= 65)
    low_conf_count = sum(1 for c in all_confidences if c < 40)

    avg_faithfulness = sum(faithfulness_vals) / len(faithfulness_vals)
    avg_relevancy = sum(relevancy_vals) / len(relevancy_vals)
    avg_hallucination = sum(hallucination_vals) / len(hallucination_vals)
    avg_bias = sum(bias_vals) / len(bias_vals)
    avg_toxicity = sum(toxicity_vals) / len(toxicity_vals)
    avg_unsupported = sum(unsupported_vals) / len(unsupported_vals)

    overall_rag_score = (
        0.25 * avg_faithfulness
        + 0.20 * avg_relevancy
        + 0.20 * (1.0 - avg_hallucination)
        + 0.15 * avg_bias
        + 0.10 * avg_toxicity
        + 0.10 * (1.0 - avg_unsupported)
    ) * 100

    return {
        "overall_rag_score": round(overall_rag_score, 1),
        "avg_faithfulness": round(avg_faithfulness, 4),
        "avg_answer_relevancy": round(avg_relevancy, 4),
        "avg_hallucination": round(avg_hallucination, 4),
        "avg_bias": round(avg_bias, 4),
        "avg_toxicity": round(avg_toxicity, 4),
        "avg_unsupported_answer_rate": round(avg_unsupported, 4),
        "avg_confidence": round(avg_confidence, 1),
        "avg_latency_ms": round(avg_latency, 1),
        "high_confidence_ratio": round(high_conf_count / n, 2) if n else 0,
        "low_confidence_ratio": round(low_conf_count / n, 2) if n else 0,
        "total_questions": n,
    }


def _generate_recommendations(metrics: dict[str, Any]) -> list[str]:
    recommendations: list[str] = []

    if metrics.get("avg_hallucination", 0) > 0.15:
        recommendations.append("High hallucination rate detected. Consider adding more specific context chunks or improving chunk quality.")
    if metrics.get("avg_faithfulness", 1) < 0.7:
        recommendations.append("Low faithfulness score. The answers may not be fully supported by the document. Review chunk overlap and retrieval top_k settings.")
    if metrics.get("avg_answer_relevancy", 1) < 0.6:
        recommendations.append("Low answer relevancy. The RAG system may be retrieving irrelevant chunks. Try reducing chunk size or improving query preprocessing.")
    if metrics.get("avg_confidence", 100) < 50:
        recommendations.append("Low overall confidence. Consider improving document text quality, adding more content, or adjusting the confidence thresholds.")
    if metrics.get("low_confidence_ratio", 0) > 0.3:
        recommendations.append("More than 30% of questions have low confidence. The document may lack sufficient detail for the generated questions.")
    if metrics.get("total_questions", 0) < 3:
        recommendations.append("Few evaluation questions were generated. Consider adding more content or more diverse topics to your document.")
    if not recommendations:
        recommendations.append("Document evaluation looks good. No critical issues detected.")

    return recommendations


def _metric_value(metrics, name: str) -> float:
    m = metrics.get(name)
    return m.value if m else 0.0


def _chunk_summary(c: dict[str, Any]) -> dict[str, Any]:
    return {
        "chunk_id": c.get("chunk_id", ""),
        "text_preview": (c.get("text", "") or "")[:150],
        "score": c.get("rerank_score") or c.get("vector_score", 0),
        "filename": c.get("filename"),
    }
