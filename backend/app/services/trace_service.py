import csv
import io
import json
import logging
from datetime import datetime

from sqlalchemy import func as sqlfunc, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trace import Trace

logger = logging.getLogger(__name__)


async def save_trace(
    db: AsyncSession,
    trace_id: str,
    original_query: str,
    rewritten_query: str | None,
    confidence_before_rewrite: float,
    confidence_after_rewrite: float | None,
    retrieval_attempts: int,
    reason_for_retry: str | None,
    contradiction_detected: bool,
    contradiction_reason: str | None,
    clarification_needed: bool,
    clarification_question: str | None,
    final_confidence: float,
    final_confidence_level: str,
    execution_path: list[str],
    graph_execution: list[dict],
    retrieval_details: list[dict],
    confidence_breakdown: dict | None,
    llm_observability: dict | None,
    session_timeline: str | None,
    answer: str | None,
    citations: list[dict],
    latencies: dict[str, float],
) -> Trace:
    trace = Trace(
        id=trace_id,
        original_query=original_query,
        rewritten_query=rewritten_query,
        confidence_before_rewrite=confidence_before_rewrite,
        confidence_after_rewrite=confidence_after_rewrite,
        retrieval_attempts=retrieval_attempts,
        reason_for_retry=reason_for_retry,
        contradiction_detected=contradiction_detected,
        contradiction_reason=contradiction_reason,
        clarification_needed=clarification_needed,
        clarification_question=clarification_question,
        final_confidence=final_confidence,
        final_confidence_level=final_confidence_level,
        execution_path=json.dumps(execution_path) if execution_path else None,
        graph_execution=json.dumps(graph_execution) if graph_execution else None,
        retrieval_details=json.dumps(retrieval_details) if retrieval_details else None,
        confidence_breakdown=json.dumps(confidence_breakdown) if confidence_breakdown else None,
        llm_observability=json.dumps(llm_observability) if llm_observability else None,
        session_timeline=session_timeline,
        answer=answer,
        citations=json.dumps(citations) if citations else None,
        latencies=json.dumps(latencies) if latencies else None,
    )
    db.add(trace)
    await db.commit()
    await db.refresh(trace)
    logger.info("Trace saved: %s", trace_id)
    return trace


async def get_trace(db: AsyncSession, trace_id: str) -> Trace | None:
    result = await db.execute(select(Trace).where(Trace.id == trace_id))
    return result.scalar_one_or_none()


async def list_traces(db: AsyncSession, skip: int = 0, limit: int = 50) -> list[Trace]:
    result = await db.execute(
        select(Trace).order_by(desc(Trace.timestamp)).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def count_traces(db: AsyncSession) -> int:
    result = await db.execute(select(sqlfunc.count(Trace.id)))
    return result.scalar() or 0


def trace_to_dict(trace: Trace) -> dict:
    return {
        "id": trace.id,
        "timestamp": trace.timestamp.isoformat() if trace.timestamp else "",
        "original_query": trace.original_query,
        "rewritten_query": trace.rewritten_query,
        "confidence_before_rewrite": trace.confidence_before_rewrite,
        "confidence_after_rewrite": trace.confidence_after_rewrite,
        "retrieval_attempts": trace.retrieval_attempts,
        "reason_for_retry": trace.reason_for_retry,
        "contradiction_detected": trace.contradiction_detected,
        "contradiction_reason": trace.contradiction_reason,
        "clarification_needed": trace.clarification_needed,
        "clarification_question": trace.clarification_question,
        "final_confidence": trace.final_confidence,
        "final_confidence_level": trace.final_confidence_level,
        "execution_path": json.loads(trace.execution_path) if trace.execution_path else [],
        "graph_execution": json.loads(trace.graph_execution) if trace.graph_execution else [],
        "retrieval_details": json.loads(trace.retrieval_details) if trace.retrieval_details else [],
        "confidence_breakdown": json.loads(trace.confidence_breakdown) if trace.confidence_breakdown else None,
        "llm_observability": json.loads(trace.llm_observability) if trace.llm_observability else None,
        "session_timeline": trace.session_timeline,
        "answer": trace.answer,
        "citations": json.loads(trace.citations) if trace.citations else [],
        "latencies": json.loads(trace.latencies) if trace.latencies else {},
    }


def export_traces_csv(traces_data: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Trace ID", "Timestamp", "Original Query", "Rewritten Query",
        "Confidence Before", "Confidence After", "Retrieval Attempts",
        "Reason For Retry", "Contradiction", "Clarification",
        "Final Confidence", "Final Level", "Execution Path", "Answer Length",
    ])
    for t in traces_data:
        writer.writerow([
            t["id"], t["timestamp"], t["original_query"], t.get("rewritten_query", "") or "",
            t["confidence_before_rewrite"], t.get("confidence_after_rewrite", "") or "",
            t["retrieval_attempts"], t.get("reason_for_retry", "") or "",
            t["contradiction_detected"], t["clarification_needed"],
            t["final_confidence"], t["final_confidence_level"],
            "; ".join(t.get("execution_path", [])),
            len(t.get("answer", "") or ""),
        ])
    return output.getvalue()


def export_traces_markdown(traces_data: list[dict]) -> str:
    lines = [
        "# SentinelRAG AI Decision Trace Report",
        "",
        f"**Generated:** {datetime.utcnow().isoformat()}",
        f"**Total Traces:** {len(traces_data)}",
        "",
        "---",
        "",
    ]
    for t in traces_data:
        lines.append(f"## Trace: {t['id']}")
        lines.append(f"- **Timestamp:** {t['timestamp']}")
        lines.append(f"- **Original Query:** {t['original_query']}")
        lines.append(f"- **Rewritten Query:** {t.get('rewritten_query', 'N/A') or 'N/A'}")
        lines.append(f"- **Confidence Before Rewrite:** {t['confidence_before_rewrite']}%")
        lines.append(f"- **Confidence After Rewrite:** {t.get('confidence_after_rewrite', 'N/A') or 'N/A'}%")
        lines.append(f"- **Retrieval Attempts:** {t['retrieval_attempts']}")
        lines.append(f"- **Reason For Retry:** {t.get('reason_for_retry', 'N/A') or 'N/A'}")
        lines.append(f"- **Contradiction Detected:** {t['contradiction_detected']}")
        if t.get("contradiction_reason"):
            lines.append(f"- **Contradiction Reason:** {t['contradiction_reason']}")
        lines.append(f"- **Clarification Needed:** {t['clarification_needed']}")
        if t.get("clarification_question"):
            lines.append(f"- **Clarification Question:** {t['clarification_question']}")
        lines.append(f"- **Final Confidence:** {t['final_confidence']}% ({t['final_confidence_level']})")
        lines.append(f"- **Execution Path:** {' → '.join(t.get('execution_path', []))}")
        lines.append(f"- **Answer Length:** {len(t.get('answer', '') or '')} chars")
        lines.append("")
        if t.get("confidence_breakdown"):
            cb = t["confidence_breakdown"]
            lines.append("### Confidence Breakdown")
            lines.append(f"- Vector Similarity: {cb.get('vector_similarity', 0):.4f} (contribution: {cb.get('vector_contribution', 0):.2f})")
            lines.append(f"- Cross-Encoder Score: {cb.get('cross_encoder_score', 0):.4f} (contribution: {cb.get('cross_encoder_contribution', 0):.2f})")
            lines.append(f"- Coverage: {cb.get('coverage', 0):.4f} (contribution: {cb.get('coverage_contribution', 0):.2f})")
            lines.append(f"- Citation Count: {cb.get('citation_count', 0)}")
            lines.append(f"- Contradiction Status: {cb.get('contradiction_status', 'none')}")
            lines.append(f"- Retry Success: {cb.get('retry_success', False)}")
            lines.append(f"- Raw Score: {cb.get('raw_score', 0):.4f}")
            lines.append(f"- Final Score: {cb.get('final_score', 0):.1f}%")
            lines.append("")
        if t.get("retrieval_details"):
            lines.append("### Retrieved Chunks")
            lines.append("| Rank | Chunk ID | Vector Score | BM25 Score | Fusion Score | Rerank Score | Selected |")
            lines.append("|------|----------|-------------|------------|--------------|--------------|----------|")
            for r in t["retrieval_details"][:10]:
                lines.append(
                    f"| {r.get('final_rank', '')} | {str(r.get('chunk_id', ''))[:8]}... | "
                    f"{r.get('vector_score', 0):.4f} | {r.get('bm25_score', 0):.4f} | "
                    f"{r.get('fusion_score', 0):.4f} | {r.get('rerank_score', 0):.4f} | "
                    f"{r.get('selected', False)} |"
                )
            lines.append("")
        if t.get("graph_execution"):
            lines.append("### Graph Execution Timeline")
            for g in t["graph_execution"]:
                nn = g.get("node_name", "?")
                et = g.get("execution_time_ms", 0)
                dec = g.get("decision", "")
                nxt = g.get("next_node", "")
                rc = g.get("retry_count", 0)
                dec_str = f" → decision: {dec}" if dec else ""
                nxt_str = f" → next: {nxt}" if nxt else ""
                lines.append(f"- **{nn}**: {et:.1f}ms (retry #{rc}){dec_str}{nxt_str}")
            lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def build_session_timeline(execution_path: list[str], graph_execution: list[dict]) -> str:
    steps = [
        ("Upload", None),
        ("OCR", None),
        ("Chunking", None),
        ("Embedding", None),
    ]
    node_map = {
        "retrieve": "Vector Search",
        "bm25": "BM25",
        "fusion": "Fusion",
        "rerank": "Cross Encoder",
        "confidence_evaluate": "Confidence",
        "rewrite_query": "Rewrite",
        "retry_retrieve": "Retry",
        "contradiction_detect": "Contradiction",
        "clarification": "Clarification",
        "generate_answer": "Answer",
    }
    seen = set()
    for p in execution_path:
        clean = p.replace("retry_retrieve", "retry_retrieve").split("(")[0]
        if clean in node_map and clean not in seen:
            seen.add(clean)
            label = node_map[clean]
            found = next((g for g in graph_execution if g.get("node_name") == clean or g.get("node_name") == p), None)
            ms = found["execution_time_ms"] if found else None
            steps.append((label, ms))

    lines = []
    for i, (label, ms) in enumerate(steps):
        prefix = "↓" if i > 0 else ""
        ms_str = f" ({ms:.0f}ms)" if ms is not None else ""
        lines.append(f"{prefix} {label}{ms_str}")
    return "\n".join(lines)
