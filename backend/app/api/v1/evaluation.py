import asyncio
import json
import logging
import uuid

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db, get_session_maker
from app.core.exceptions import AppException
from app.models.document import Document
from app.models.document_evaluation import DocumentEvaluation
from app.models.evaluation_run import EvaluationRun
from app.models.user import User
from app.services.document_evaluation_service import evaluate_document
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


async def _run_evaluation_background(eval_id: str, dataset_path: str, total: int) -> None:
    tasks = _load_tasks()
    tasks[eval_id] = {"status": "running", "progress": 0, "total": total, "error": None}
    _save_tasks(tasks)

    session_maker = get_session_maker()
    try:
        async with session_maker() as db:
            result = await _runner.run(db=db, dataset_path=dataset_path, eval_id=eval_id)

        report_files = _report_gen.generate_all(result)
        result["reports"] = report_files

        visualizations = _visualizer.generate_all(
            baseline_metrics=result["summary"]["baseline"],
            sentinel_metrics=result["summary"]["sentinel"],
            comparison=result["summary"]["comparison"],
        )
        result["visualizations"] = visualizations

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
        tasks = _load_tasks()
        tasks[eval_id] = {"status": "failed", "progress": 0, "total": total, "error": str(exc)}
        _save_tasks(tasks)


@router.post("/evaluate")
async def run_evaluation(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    eval_id = str(uuid.uuid4())
    dataset_path = str(Path(__file__).resolve().parent.parent.parent.parent / "evaluation" / "datasets" / "benchmark.json")
    total_questions = _count_questions(dataset_path)

    run = EvaluationRun(evaluation_id=eval_id, user_id=current_user.id, status="running")
    db.add(run)
    await db.commit()

    task = asyncio.create_task(_run_evaluation_background(eval_id, dataset_path, total_questions))
    _eval_tasks.add(task)
    task.add_done_callback(_eval_tasks.discard)

    return {
        "evaluation_id": eval_id,
        "status": "running",
        "total_questions": total_questions,
    }


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
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    result = _report_gen.load_latest_result()
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
    history = _report_gen.load_history()
    return [h for h in history if h.get("evaluation_id") in user_eval_ids]


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
