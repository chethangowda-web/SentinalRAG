import asyncio
import json
import logging
import uuid

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db, get_session_maker
from app.core.exceptions import AppException
from app.models.document import Document
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
