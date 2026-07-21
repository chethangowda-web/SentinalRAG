import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from evaluation.dataset import load_dataset, get_dataset_summary
from evaluation.reports.report_generator import ReportGenerator
from evaluation.reports.visualizer import Visualizer
from evaluation.services.runner import EvaluationRunner

logger = logging.getLogger(__name__)

router = APIRouter(tags=["evaluation"])

_runner = EvaluationRunner()
_report_gen = ReportGenerator()
_visualizer = Visualizer()


@router.post("/evaluate")
async def run_evaluation(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        result = await _runner.run(db=db)

        report_files = _report_gen.generate_all(result)
        result["reports"] = report_files

        visualizations = _visualizer.generate_all(
            baseline_metrics=result["summary"]["baseline"],
            sentinel_metrics=result["summary"]["sentinel"],
            comparison=result["summary"]["comparison"],
        )
        result["visualizations"] = visualizations

        return {
            "status": "completed",
            "evaluation_id": result["evaluation_id"],
            "timestamp": result["timestamp"],
            "total_questions": result["total_questions"],
            "summary": result["summary"],
            "reports": report_files,
            "visualizations": visualizations,
            "failure_modes": result.get("failure_modes", {}),
        }
    except Exception as e:
        logger.exception("Evaluation failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {e!s}")


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
