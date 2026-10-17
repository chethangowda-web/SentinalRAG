import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db, get_session_maker
from app.core.exceptions import AppException
from app.models.document import Document
from app.models.document_evaluation import DocumentEvaluation
from app.models.evaluation_run import EvaluationRun
from app.models.user import User
from app.services.benchmark_service import benchmark_status, start_loading
from app.services.document_evaluation_service import evaluate_document
from app.services.llm import llm_status
from evaluation.behaviour import behaviour_checks
from evaluation.dataset import load_dataset, get_dataset_summary
from evaluation.reports.report_generator import ReportGenerator
from evaluation.reports.visualizer import Visualizer
from evaluation.services.runner import EvaluationRunner

logger = logging.getLogger(__name__)

router = APIRouter(tags=["evaluation"])

_eval_tasks: set[asyncio.Task] = set()
_runner = EvaluationRunner()
_report_gen = ReportGenerator()
_visualizer = Visualizer()

_STATUS_FILE = Path("/tmp/eval_tasks.json")


def _load_tasks() -> dict[str, Any]:
    if _STATUS_FILE.exists():
        try:
            return json.loads(_STATUS_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_tasks(tasks: dict[str, Any]) -> None:
    _STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATUS_FILE.write_text(json.dumps(tasks, indent=2))


def _count_questions(dataset_path: str) -> int:
    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            import json
            data = json.load(f)
            return len(data) if isinstance(data, list) else 18
    except Exception:
        return 18


async def _set_run_status(eval_id: str, status: str) -> None:
    try:
        async with get_session_maker()() as db:
            await db.execute(update(EvaluationRun).where(EvaluationRun.evaluation_id == eval_id).values(status=status))
            await db.commit()
    except Exception:
        logger.exception("Could not record status %s for evaluation %s", status, eval_id)


async def recover_interrupted_runs(db: AsyncSession) -> int:
    """Runs that were "running" when the process restarted can never finish; mark them failed."""
    running = (await db.execute(select(EvaluationRun).where(EvaluationRun.status == "running"))).scalars().all()
    for run in running:
        # Runs from before status was recorded finished fine if their result file exists
        run.status = "completed" if run.result_json or _report_gen.load_result(run.evaluation_id) is not None else "failed"
    await db.commit()
    return len(running)


async def _latest_report_for(db: AsyncSession, user_id: str) -> dict[str, Any] | None:
    runs = await db.execute(
        select(EvaluationRun.evaluation_id, EvaluationRun.result_json)
        .where(EvaluationRun.user_id == user_id)  # a result exists only for runs that finished
        .order_by(EvaluationRun.created_at.desc())
    )
    for evaluation_id, result_json in runs.all():
        result = _parse_result(result_json) or _report_gen.load_result(evaluation_id)
        if result is not None and result.get("per_question"):  # a run that answered nothing is not a report
            result["behaviour"] = behaviour_checks(result)
            return result
    return None


def _parse_result(result_json: str | None) -> dict[str, Any] | None:
    if not result_json:
        return None
    try:
        return json.loads(result_json)
    except (TypeError, ValueError):
        logger.warning("Stored evaluation result is not valid JSON")
        return None


async def _store_result(eval_id: str, result: dict[str, Any]) -> None:
    try:
        async with get_session_maker()() as db:
            await db.execute(
                update(EvaluationRun).where(EvaluationRun.evaluation_id == eval_id).values(result_json=json.dumps(result, default=str))
            )
            await db.commit()
    except Exception:
        logger.exception("Could not store the result of evaluation %s", eval_id)


async def _run_evaluation_background(
    eval_id: str,
    dataset_path: str,
    total: int,
    user_id: str | None = None,
    questions: list[dict[str, Any]] | None = None,
) -> None:
    tasks = _load_tasks()
    tasks[eval_id] = {"status": "running", "progress": 0, "total": total, "error": None, "stage": "questions"}
    _save_tasks(tasks)

    session_maker = get_session_maker()
    try:
        async with session_maker() as db:
            result = await _runner.run(db=db, dataset_path=dataset_path, eval_id=eval_id, user_id=user_id, questions=questions)

        tasks = _load_tasks()
        tasks[eval_id] = {**tasks.get(eval_id, {}), "stage": "report"}
        _save_tasks(tasks)
        report_files = _report_gen.generate_all(result)
        result["reports"] = report_files

        visualizations = _visualizer.generate_all(
            baseline_metrics=result["summary"]["baseline"],
            sentinel_metrics=result["summary"]["sentinel"],
            comparison=result["summary"]["comparison"],
        )
        result["visualizations"] = visualizations

        await _store_result(eval_id, result)
        await _set_run_status(eval_id, "completed")
        tasks = _load_tasks()
        tasks[eval_id] = {
            "status": "completed",
            "progress": result["total_questions"],
            "total": result["total_questions"],
            "error": None,
        }
        _save_tasks(tasks)

    except Exception as exc:
        logger.exception("Background evaluation %s failed", eval_id)
        await _set_run_status(eval_id, "failed")
        tasks = _load_tasks()
        tasks[eval_id] = {"status": "failed", "progress": 0, "total": total, "error": str(exc)}
        _save_tasks(tasks)


@router.post("/evaluate")
async def run_evaluation(
    full: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    quota = llm_status()
    if quota["exhausted"]:
        raise AppException(
            status_code=409,
            detail=f"The AI model's request quota is used up (resets in about {max(1, quota['retry_after_seconds'] // 3600)} hour(s)); an evaluation would only produce fallback answers.",
        )
    benchmark = await benchmark_status(db, current_user.id)
    if not benchmark["ready"]:
        raise AppException(
            status_code=409,
            detail="The benchmark's sample documents are not loaded yet. Load them first (POST /api/v1/evaluation/benchmark/setup).",
        )
    in_flight = await db.execute(
        select(EvaluationRun.id).where(
            EvaluationRun.user_id == current_user.id,
            EvaluationRun.status == "running",
            EvaluationRun.created_at > datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=30),
        )
    )
    if in_flight.first() is not None:
        raise AppException(status_code=409, detail="An evaluation is already running.")

    eval_id = str(uuid.uuid4())
    dataset_path = str(Path(__file__).resolve().parent.parent.parent.parent / "evaluation" / "datasets" / "benchmark.json")
    # The quick set (one or two questions per kind) finishes in about a minute; `full` runs all of them
    questions = load_dataset(dataset_path)
    if not full:
        questions = [q for q in questions if "quick" in q.get("tags", [])] or questions
    total_questions = len(questions)

    run = EvaluationRun(evaluation_id=eval_id, user_id=current_user.id, status="running")
    db.add(run)
    await db.commit()

    task = asyncio.create_task(_run_evaluation_background(eval_id, dataset_path, total_questions, current_user.id, questions))
    _eval_tasks.add(task)
    task.add_done_callback(_eval_tasks.discard)

    return {
        "evaluation_id": eval_id,
        "status": "running",
        "total_questions": total_questions,
    }


@router.get("/evaluation/latest")
async def get_latest_evaluation_state(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Everything the evaluation page needs in one call: the last report, any run in flight, benchmark readiness.

    Unlike /evaluation/report this never 404s, and a run in progress survives a page reload.
    """
    latest = (await db.execute(
        select(EvaluationRun).where(EvaluationRun.user_id == current_user.id).order_by(EvaluationRun.created_at.desc()).limit(1)
    )).scalar_one_or_none()

    run = None
    if latest is not None:
        task = _load_tasks().get(latest.evaluation_id, {})
        running = latest.status == "running"
        run = {
            "evaluation_id": latest.evaluation_id,
            "status": latest.status,
            "progress": task.get("progress", 0) if running else task.get("total", 0),
            "total": task.get("total", 18),
            "error": task.get("error"),
            "stage": task.get("stage") if running else None,
            "steps": task.get("steps") if running else None,
        }

    return {
        "report": await _latest_report_for(db, current_user.id),
        "run": run,
        "benchmark": await benchmark_status(db, current_user.id),
    }


@router.post("/evaluation/benchmark/setup", status_code=202)
async def setup_benchmark(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Load the benchmark's six sample documents into this account (in the background)."""
    status = await benchmark_status(db, current_user.id)
    if not status["ready"]:
        start_loading(current_user.id)
        status = {**status, "loading": True}
    return status


@router.get("/evaluation/status/{evaluation_id}")
async def get_evaluation_status(
    evaluation_id: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    tasks = _load_tasks()
    task = tasks.get(evaluation_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Evaluation {evaluation_id} not found")
    return {"evaluation_id": evaluation_id, **task}


@router.get("/evaluation/report")
async def get_latest_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    result = await _latest_report_for(db, current_user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="No evaluation results found. Run /api/v1/evaluate first.")
    return result


@router.get("/evaluation/history")
async def get_evaluation_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    from sqlalchemy import select

    result = await db.execute(
        select(EvaluationRun.evaluation_id, EvaluationRun.status, EvaluationRun.created_at)
        .where(EvaluationRun.user_id == current_user.id)
        .order_by(EvaluationRun.created_at.desc())
    )
    runs = result.all()
    user_eval_ids = {r.evaluation_id for r in runs}
    history = [h for h in _report_gen.load_history() if h.get("evaluation_id") in user_eval_ids]
    known = {h.get("evaluation_id") for h in history}

    # Runs whose history file entry was lost with the container: rebuild them from the stored result
    stored = await db.execute(
        select(EvaluationRun.evaluation_id, EvaluationRun.created_at, EvaluationRun.result_json)
        .where(EvaluationRun.user_id == current_user.id, EvaluationRun.result_json.is_not(None))
        .order_by(EvaluationRun.created_at.desc())
        .limit(20)
    )
    for evaluation_id, created_at, result_json in stored.all():
        if evaluation_id in known:
            continue
        parsed = _parse_result(result_json) or {}
        history.append({
            "evaluation_id": evaluation_id,
            "timestamp": parsed.get("timestamp") or (created_at.isoformat() if created_at else None),
            "total_questions": parsed.get("total_questions"),
            "dataset": parsed.get("dataset") or "benchmark",
        })
    return sorted(history, key=lambda h: h.get("timestamp") or "", reverse=True)


@router.post("/evaluate/document/{document_id}")
async def evaluate_single_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    logger.info("Per-document evaluation request: document=%s user=%s", document_id, current_user.id)

    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    if document.status != "embedded":
        raise AppException(
            status_code=400,
            detail=f"Document {document_id} has status '{document.status}'. Must be 'embedded' first.",
        )

    try:
        eval_result = await evaluate_document(document_id, db, user_id=current_user.id)
        return eval_result
    except Exception as e:
        logger.exception("Per-document evaluation failed for %s", document_id)
        raise AppException(status_code=500, detail=f"Document evaluation failed: {e}")


@router.get("/evaluation/dataset")
async def get_dataset_info(
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    try:
        data = load_dataset()
        summary = get_dataset_summary(data)
        return {
            "status": "loaded",
            "path": str(_report_gen.results_dir.parent / "datasets" / "benchmark.json"),
            "summary": summary,
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evaluations/documents")
async def list_document_evaluations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(DocumentEvaluation)
        .where(DocumentEvaluation.user_id == current_user.id)
        .order_by(DocumentEvaluation.created_at.desc())
    )
    evals = result.scalars().all()
    return [
        {
            "id": e.id,
            "document_id": e.document_id,
            "overall_score": e.overall_score,
            "faithfulness": e.faithfulness,
            "correctness": e.correctness,
            "answer_relevancy": e.answer_relevancy,
            "context_recall": e.context_recall,
            "precision": e.precision,
            "hallucination_rate": e.hallucination_rate,
            "retrieval_score": e.retrieval_score,
            "ocr_confidence": e.ocr_confidence,
            "processing_time": e.processing_time,
            "total_questions": e.total_questions,
            "status": e.status,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in evals
    ]


@router.get("/evaluations/documents/{document_id}")
async def get_document_evaluation(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    result = await db.execute(
        select(DocumentEvaluation)
        .where(
            DocumentEvaluation.document_id == document_id,
            DocumentEvaluation.user_id == current_user.id,
        )
    )
    evaluation = result.scalar_one_or_none()
    if evaluation is None:
        raise HTTPException(status_code=404, detail=f"No evaluation found for document {document_id}")

    detail = {}
    if evaluation.eval_data:
        try:
            detail = json.loads(evaluation.eval_data)
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "id": evaluation.id,
        "document_id": evaluation.document_id,
        "overall_score": evaluation.overall_score,
        "faithfulness": evaluation.faithfulness,
        "correctness": evaluation.correctness,
        "answer_relevancy": evaluation.answer_relevancy,
        "context_recall": evaluation.context_recall,
        "precision": evaluation.precision,
        "hallucination_rate": evaluation.hallucination_rate,
        "retrieval_score": evaluation.retrieval_score,
        "ocr_confidence": evaluation.ocr_confidence,
        "processing_time": evaluation.processing_time,
        "total_questions": evaluation.total_questions,
        "status": evaluation.status,
        "error": evaluation.error,
        "created_at": evaluation.created_at.isoformat() if evaluation.created_at else None,
        "detail": detail,
    }


@router.get("/evaluations/documents/compare/{document_id1}/{document_id2}")
async def compare_document_evaluations(
    document_id1: str,
    document_id2: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    result = await db.execute(
        select(DocumentEvaluation).where(
            DocumentEvaluation.document_id.in_([document_id1, document_id2]),
            DocumentEvaluation.user_id == current_user.id,
        )
    )
    evaluations = result.scalars().all()
    if len(evaluations) != 2:
        raise HTTPException(status_code=404, detail="Could not find evaluations for both documents")

    eval_map = {e.document_id: e for e in evaluations}
    doc1 = eval_map.get(document_id1)
    doc2 = eval_map.get(document_id2)
    if not doc1 or not doc2:
        raise HTTPException(status_code=404, detail="Could not find evaluations for both documents")

    metrics = ["overall_score", "faithfulness", "correctness", "answer_relevancy",
               "context_recall", "precision", "hallucination_rate", "retrieval_score"]

    comparison = {}
    for m in metrics:
        v1 = getattr(doc1, m, 0) or 0
        v2 = getattr(doc2, m, 0) or 0
        diff = v1 - v2
        comparison[m] = {
            "document1": v1,
            "document2": v2,
            "difference": round(diff, 4),
            "better": "document1" if diff > 0 else ("document2" if diff < 0 else "tie"),
        }

    return {
        "document1": {
            "document_id": doc1.document_id,
            "overall_score": doc1.overall_score,
        },
        "document2": {
            "document_id": doc2.document_id,
            "overall_score": doc2.overall_score,
        },
        "comparison": comparison,
    }


@router.get("/evaluations/dashboard")
async def get_evaluation_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    result = await db.execute(
        select(DocumentEvaluation)
        .where(
            DocumentEvaluation.user_id == current_user.id,
            DocumentEvaluation.status == "completed",
        )
    )
    evals = result.scalars().all()

    if not evals:
        return {
            "total_evaluated": 0,
            "avg_overall_score": 0,
            "avg_faithfulness": 0,
            "avg_correctness": 0,
            "avg_answer_relevancy": 0,
            "avg_context_recall": 0,
            "avg_precision": 0,
            "avg_hallucination_rate": 0,
            "avg_retrieval_score": 0,
            "avg_processing_time": 0,
            "total_questions": 0,
        }

    n = len(evals)
    return {
        "total_evaluated": n,
        "avg_overall_score": round(sum(e.overall_score or 0 for e in evals) / n, 4),
        "avg_faithfulness": round(sum(e.faithfulness or 0 for e in evals) / n, 4),
        "avg_correctness": round(sum(e.correctness or 0 for e in evals) / n, 4),
        "avg_answer_relevancy": round(sum(e.answer_relevancy or 0 for e in evals) / n, 4),
        "avg_context_recall": round(sum(e.context_recall or 0 for e in evals) / n, 4),
        "avg_precision": round(sum(e.precision or 0 for e in evals) / n, 4),
        "avg_hallucination_rate": round(sum(e.hallucination_rate or 0 for e in evals) / n, 4),
        "avg_retrieval_score": round(sum(e.retrieval_score or 0 for e in evals) / n, 4),
        "avg_processing_time": round(sum(e.processing_time or 0 for e in evals) / n, 2),
        "total_questions": sum(e.total_questions or 0 for e in evals),
    }
