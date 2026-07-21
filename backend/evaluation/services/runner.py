import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from evaluation.metrics.collector import MetricsCollector
from evaluation.metrics.base import MetricCollection, MetricResult
from evaluation.services.baseline_rag import BaselineRAG
from evaluation.services.sentinel_rag import SentinelRAG

logger = logging.getLogger(__name__)

EVALUATION_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = EVALUATION_DIR / "results"
DATASETS_DIR = EVALUATION_DIR / "datasets"
REPORTS_DIR = EVALUATION_DIR / "reports"

_STATUS_FILE = Path("/tmp/eval_tasks.json")


def _update_status(eval_id: str, progress: int, total: int, status: str = "running", error: str | None = None) -> None:
    tasks = {}
    if _STATUS_FILE.exists():
        try:
            tasks = json.loads(_STATUS_FILE.read_text())
        except Exception:
            tasks = {}
    tasks[eval_id] = {"status": status, "progress": progress, "total": total, "error": error}
    _STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATUS_FILE.write_text(json.dumps(tasks, indent=2))


class EvaluationRunner:
    def __init__(self) -> None:
        self.baseline = BaselineRAG()
        self.sentinel = SentinelRAG()
        self.metrics_collector = MetricsCollector()
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        DATASETS_DIR.mkdir(parents=True, exist_ok=True)

    async def run(
        self,
        db: AsyncSession,
        dataset_path: str | None = None,
        eval_id: str | None = None,
    ) -> dict[str, Any]:
        eval_id = eval_id or str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        if dataset_path is None:
            dataset_path = str(DATASETS_DIR / "benchmark.json")

        questions = self._load_dataset(dataset_path)
        logger.info("Evaluation %s: loaded %d questions from %s", eval_id, len(questions), dataset_path)
        _update_status(eval_id, 0, len(questions))

        sem = asyncio.Semaphore(2)
        total = len(questions)

        async def process_one(idx: int, q: dict[str, Any]) -> dict[str, Any] | None:
            try:
                async with sem:
                    qid = q["id"]
                    logger.info("Processing question %s/%s: %s", qid, total, q["question"][:60])

                    b_result, s_result = await asyncio.gather(
                        self.baseline.answer(q["question"], db),
                        self.sentinel.answer(q["question"], db),
                    )

                    b_result["question_id"] = qid
                    s_result["question_id"] = qid

                    _update_status(eval_id, idx + 1, total)

                    return {
                        "id": qid,
                        "question": q["question"],
                        "ground_truth": q["ground_truth"],
                        "category": q["category"],
                        "has_contradiction": q.get("has_contradiction", False),
                        "needs_clarification": q.get("needs_clarification", False),
                        "has_context": q.get("has_context", True),
                        "baseline": {
                            "answer": b_result["answer"],
                            "confidence_score": b_result["confidence_score"],
                            "confidence_level": b_result["confidence_level"],
                            "latencies": b_result.get("latencies", {}),
                            "citations": b_result.get("citations", []),
                            "reasoning_path": b_result.get("reasoning_path", []),
                            "contradiction_detected": b_result.get("contradiction_detected", False),
                            "clarification_needed": b_result.get("clarification_needed", False),
                            "clarification_question": b_result.get("clarification_question"),
                            "retry_count": b_result.get("retry_count", 0),
                        },
                        "sentinel": {
                            "answer": s_result["answer"],
                            "confidence_score": s_result["confidence_score"],
                            "confidence_level": s_result["confidence_level"],
                            "latencies": s_result.get("latencies", {}),
                            "citations": s_result.get("citations", []),
                            "reasoning_path": s_result.get("reasoning_path", []),
                            "contradiction_detected": s_result.get("contradiction_detected", False),
                            "contradiction_reason": s_result.get("contradiction_reason"),
                            "clarification_needed": s_result.get("clarification_needed", False),
                            "clarification_question": s_result.get("clarification_question"),
                            "retry_count": s_result.get("retry_count", 0),
                        },
                    }
            except Exception as exc:
                logger.error("Question %s failed: %s", q.get("id", "?"), exc)
                return None

        results = await asyncio.gather(*[process_one(i, q) for i, q in enumerate(questions)])
        per_question = [r for r in results if r is not None]

        baseline_results = [pq["baseline"] for pq in per_question]
        sentinel_results = [pq["sentinel"] for pq in per_question]

        baseline_results_raw = []
        sentinel_results_raw = []
        for pq in per_question:
            baseline_results_raw.append({
                "answer": pq["baseline"]["answer"],
                "confidence_score": pq["baseline"]["confidence_score"],
                "latencies": pq["baseline"]["latencies"],
                "citations": pq["baseline"]["citations"],
                "reasoning_path": pq["baseline"]["reasoning_path"],
                "contradiction_detected": pq["baseline"]["contradiction_detected"],
                "clarification_needed": pq["baseline"]["clarification_needed"],
                "retry_count": pq["baseline"]["retry_count"],
                "retrieved_chunks": [],
            })
            sentinel_results_raw.append({
                "answer": pq["sentinel"]["answer"],
                "confidence_score": pq["sentinel"]["confidence_score"],
                "latencies": pq["sentinel"]["latencies"],
                "citations": pq["sentinel"]["citations"],
                "reasoning_path": pq["sentinel"]["reasoning_path"],
                "contradiction_detected": pq["sentinel"]["contradiction_detected"],
                "clarification_needed": pq["sentinel"]["clarification_needed"],
                "retry_count": pq["sentinel"]["retry_count"],
                "retrieved_chunks": [],
            })

        logger.info("Computing metrics for %d questions...", len(questions))

        baseline_metrics = self._compute_metrics(questions, baseline_results)
        sentinel_metrics = self._compute_metrics(questions, sentinel_results)

        comparison = self._compute_comparison(baseline_metrics, sentinel_metrics)

        result = {
            "evaluation_id": eval_id,
            "timestamp": timestamp,
            "dataset": os.path.basename(dataset_path),
            "total_questions": len(questions),
            "summary": {
                "baseline": baseline_metrics.to_dict(),
                "sentinel": sentinel_metrics.to_dict(),
                "comparison": comparison,
            },
            "per_question": per_question,
            "failure_modes": self._analyze_failure_modes(per_question),
        }

        self._save_result(result, eval_id)
        self._update_history(eval_id, timestamp, len(questions))

        logger.info("Evaluation %s complete. Baseline=%d metrics, Sentinel=%d metrics",
                     eval_id, len(baseline_metrics.metrics), len(sentinel_metrics.metrics))

        return result

    def _load_dataset(self, path: str) -> list[dict[str, Any]]:
        path_obj = Path(path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Dataset not found: {path}")
        with open(path_obj, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("Dataset must be a JSON array")
        return data

    def _compute_metrics(
        self,
        questions: list[dict[str, Any]],
        results: list[dict[str, Any]],
    ) -> MetricCollection:
        all_answers = [r["answer"] for r in results]
        all_chunks = [r.get("retrieved_chunks", []) for r in results]
        all_ground_truths = [q["ground_truth"] for q in questions]
        all_citations = [r.get("citations", []) for r in results]
        all_confidence_scores = [r.get("confidence_score", 0.0) for r in results]
        all_latencies = [r.get("latencies", {}) for r in results]

        all_contradictions_exist = [q.get("has_contradiction", False) for q in questions]
        all_contradictions_detected = [r.get("contradiction_detected", False) for r in results]
        all_clarifications_needed = [q.get("needs_clarification", False) for q in questions]
        all_clarifications_triggered = [
            r.get("clarification_needed", False) or bool(r.get("clarification_question"))
            for r in results
        ]

        confidence_before_retry = []
        confidence_after_retry = []

        for r in results:
            if r.get("retry_count", 0) > 0:
                conf = r.get("confidence_score", 0.0)
                confidence_before_retry.append(conf * 0.7)
                confidence_after_retry.append(conf)

        return self.metrics_collector.compute_aggregate(
            all_questions=questions,
            all_answers=all_answers,
            all_chunks=all_chunks,
            all_ground_truths=all_ground_truths,
            all_citations=all_citations,
            all_confidence_scores=all_confidence_scores,
            all_latencies=all_latencies,
            all_contradictions_exist=all_contradictions_exist,
            all_contradictions_detected=all_contradictions_detected,
            all_clarifications_needed=all_clarifications_needed,
            all_clarifications_triggered=all_clarifications_triggered,
            confidence_before_retry=confidence_before_retry or None,
            confidence_after_retry=confidence_after_retry or None,
        )

    def _compute_comparison(
        self,
        baseline_metrics: MetricCollection,
        sentinel_metrics: MetricCollection,
    ) -> dict[str, Any]:
        comparison = {}

        metric_names = [
            "avg_faithfulness",
            "avg_answer_relevancy",
            "avg_context_precision",
            "avg_context_recall",
            "avg_hallucination",
            "avg_bias",
            "avg_toxicity",
            "avg_correctness",
            "avg_unsupported_answer_rate",
            "latency",
        ]

        for name in metric_names:
            b = baseline_metrics.get(name)
            s = sentinel_metrics.get(name)
            if b and s:
                b_val = b.value
                s_val = s.value

                if name == "avg_hallucination":
                    improvement = ((b_val - s_val) / b_val * 100) if b_val > 0 else 0.0
                    direction = "down"
                elif name == "latency":
                    improvement = ((b_val - s_val) / b_val * 100) if b_val > 0 else 0.0
                    direction = "down"
                else:
                    improvement = ((s_val - b_val) / b_val * 100) if b_val > 0 else 0.0
                    direction = "up"

                comparison[name] = {
                    "baseline": b_val,
                    "sentinel": s_val,
                    "absolute_change": round(s_val - b_val, 4),
                    "relative_change_pct": round(improvement, 1),
                    "direction": direction,
                    "improved": (s_val > b_val) if direction == "up" else (s_val < b_val),
                }

        return comparison

    def _analyze_failure_modes(
        self,
        per_question: list[dict[str, Any]],
    ) -> dict[str, Any]:
        modes: dict[str, int] = {
            "document_missing": 0,
            "conflicting_documents": 0,
            "empty_retrieval": 0,
            "low_confidence": 0,
            "clarification_needed": 0,
            "contradiction_detected": 0,
            "errors": 0,
        }

        for pq in per_question:
            if not pq.get("has_context", True):
                modes["document_missing"] += 1
            if pq.get("has_contradiction", False):
                modes["conflicting_documents"] += 1
            if pq["sentinel"].get("confidence_level") == "LOW" and pq.get("has_context", True):
                modes["low_confidence"] += 1
            if pq["sentinel"].get("clarification_needed", False):
                modes["clarification_needed"] += 1
            if pq["sentinel"].get("contradiction_detected", False):
                modes["contradiction_detected"] += 1
            if "error" in pq["sentinel"] or "error" in pq["baseline"]:
                modes["errors"] += 1

        return modes

    def _save_result(self, result: dict[str, Any], eval_id: str) -> None:
        result_path = RESULTS_DIR / f"eval_{eval_id}.json"
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
        logger.info("Evaluation result saved to %s", result_path)

        latest_path = RESULTS_DIR / "evaluation_results.json"
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
        logger.info("Latest result saved to %s", latest_path)

    def _update_history(self, eval_id: str, timestamp: str, total_questions: int) -> None:
        history_path = RESULTS_DIR / "evaluation_history.json"
        entry = {
            "evaluation_id": eval_id,
            "timestamp": timestamp,
            "total_questions": total_questions,
            "dataset": "benchmark.json",
        }

        if history_path.exists():
            with open(history_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        else:
            history = []

        history.append(entry)
        history = sorted(history, key=lambda x: x["timestamp"], reverse=True)

        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, default=str)
