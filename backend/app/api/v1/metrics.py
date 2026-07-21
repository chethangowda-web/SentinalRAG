import logging

from fastapi import APIRouter

from app.core.metrics import get_metrics_collector
from app.core.resource_tracker import get_resource_tracker
from app.schemas.metrics import (
    PerformanceMetricsResponse,
    SystemMetricsResponse,
    ErrorMetricsResponse,
    MetricSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["metrics"])


@router.get("/metrics/performance", response_model=PerformanceMetricsResponse)
async def get_performance_metrics():
    collector = get_metrics_collector()
    raw = collector.get_performance_summary()

    latencies = {}
    for key, summary in raw["latencies"].items():
        latencies[key] = MetricSummary(**summary)

    errors_raw = raw["errors"]
    errors: dict[str, int | dict[str, int]] = {
        "total": errors_raw.get("total", 0),
        "by_type": errors_raw.get("by_type", {}),
    }

    return PerformanceMetricsResponse(
        latencies=latencies,
        counters=raw["counters"],
        errors=errors,
    )


@router.get("/metrics/system", response_model=SystemMetricsResponse)
async def get_system_metrics():
    tracker = get_resource_tracker()
    summary = tracker.summarize()

    return SystemMetricsResponse(
        cpu={
            "avg_percent": round(summary.cpu_avg, 2),
            "max_percent": round(summary.cpu_max, 2),
            "min_percent": round(summary.cpu_min, 2),
        },
        memory={
            "avg_mb": round(summary.memory_avg_mb, 2),
            "max_mb": round(summary.memory_max_mb, 2),
            "min_mb": round(summary.memory_min_mb, 2),
            "avg_percent": round(summary.memory_avg_percent, 2),
            "peak_percent": round(summary.memory_peak_percent, 2),
        },
        disk={
            "total_mb": round(summary.disk_total_mb, 2),
            "used_mb": round(summary.disk_used_mb, 2),
            "free_mb": round(summary.disk_free_mb, 2),
        },
        uptime_seconds=summary.samples,
        samples=summary.samples,
        duration_seconds=round(summary.duration_seconds, 2),
    )


@router.get("/metrics/errors", response_model=ErrorMetricsResponse)
async def get_error_metrics():
    collector = get_metrics_collector()
    errors = collector.get_errors()
    return ErrorMetricsResponse(
        total=errors["total"],
        by_type=errors["by_type"],
    )
