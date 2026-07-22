import asyncio
import json
import logging
import uuid

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.database import get_session_maker
from evaluation.dataset import load_dataset, get_dataset_summary
from evaluation.reports.report_generator import ReportGenerator
from evaluation.reports.visualizer import Visualizer
from evaluation.services.runner import EvaluationRunner

logger = logging.getLogger(__name__)

router = APIRouter(tags=["evaluation"])

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


async def _run_evaluation_background(eval_id: str, dataset_path: str) -> None:
    tasks = _load_tasks()
    tasks[eval_id] = {"status": "running", "progress": 0, "total": 18, "error": None}
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
        tasks[eval_id] = {"status": "failed", "progress": 0, "total": 18, "error": str(exc)}
        _save_tasks(tasks)


@router.post("/evaluate")
async def run_evaluation() -> dict[str, Any]:
    eval_id = str(uuid.uuid4())
    dataset_path = str(Path(__file__).resolve().parent.parent.parent.parent / "evaluation" / "datasets" / "benchmark.json")

    asyncio.create_task(_run_evaluation_background(eval_id, dataset_path))

    return {
        "evaluation_id": eval_id,
        "status": "running",
        "total_questions": 18,
    }


@router.get("/evaluation/status/{evaluation_id}")
async def get_evaluation_status(evaluation_id: str) -> dict[str, Any]:
    tasks = _load_tasks()
    task = tasks.get(evaluation_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Evaluation {evaluation_id} not found")
    return {"evaluation_id": evaluation_id, **task}


@router.get("/evaluation/report")
async def get_latest_report() -> dict[str, Any]:
    result = _report_gen.load_latest_result()
    if result is None:
        raise HTTPException(status_code=404, detail="No evaluation results found. Run /api/v1/evaluate first.")
    return result


@router.get("/evaluation/history")
async def get_evaluation_history() -> list[dict[str, Any]]:
    history = _report_gen.load_history()
    return history


@router.get("/evaluation/dataset")
async def get_dataset_info() -> dict[str, Any]:
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
