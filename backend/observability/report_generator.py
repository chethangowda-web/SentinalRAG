import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.metrics import get_metrics_collector
from app.core.resource_tracker import get_resource_tracker

logger = logging.getLogger(__name__)


class ObservabilityReportGenerator:
    def __init__(self, output_dir: str = "performance"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def generate_latency_report(self) -> dict[str, Any]:
        collector = get_metrics_collector()
        raw = collector.get_performance_summary()
        return {
            "timestamp": self._timestamp(),
            "type": "latency_report",
            "latencies": raw["latencies"],
            "counters": raw["counters"],
            "errors": raw["errors"],
        }

    def generate_resource_report(self) -> dict[str, Any]:
        tracker = get_resource_tracker()
        summary = tracker.summarize()
        return {
            "timestamp": self._timestamp(),
            "type": "resource_report",
            "cpu": {
                "avg_percent": round(summary.cpu_avg, 2),
                "max_percent": round(summary.cpu_max, 2),
                "min_percent": round(summary.cpu_min, 2),
            },
            "memory": {
                "avg_mb": round(summary.memory_avg_mb, 2),
                "max_mb": round(summary.memory_max_mb, 2),
                "min_mb": round(summary.memory_min_mb, 2),
                "avg_percent": round(summary.memory_avg_percent, 2),
                "peak_percent": round(summary.memory_peak_percent, 2),
            },
            "disk": {
                "total_mb": round(summary.disk_total_mb, 2),
                "used_mb": round(summary.disk_used_mb, 2),
                "free_mb": round(summary.disk_free_mb, 2),
            },
            "samples": summary.samples,
            "duration_seconds": round(summary.duration_seconds, 2),
        }

    def generate_error_summary(self) -> dict[str, Any]:
        collector = get_metrics_collector()
        errors = collector.get_errors()
        return {
            "timestamp": self._timestamp(),
            "type": "error_summary",
            "total_errors": errors["total"],
            "errors_by_type": errors["by_type"],
            "total_requests": collector.get_counters().get("component_calls.total", 0),
            "error_rate": round(
                errors["total"] / max(collector.get_counters().get("component_calls.total", 1), 1) * 100,
                2,
            ),
        }

    def generate_retry_statistics(self) -> dict[str, Any]:
        collector = get_metrics_collector()
        counters = collector.get_counters()
        retries = counters.get("retries.total", 0)
        chat_calls = counters.get("component_calls.chat", 0)
        retry_rate = round(retries / max(chat_calls, 1) * 100, 2)
        return {
            "timestamp": self._timestamp(),
            "type": "retry_statistics",
            "total_retries": retries,
            "chat_calls": chat_calls,
            "retry_rate_pct": retry_rate,
            "avg_retries_per_chat": round(retries / max(chat_calls, 1), 2),
        }

    def generate_confidence_distribution(self) -> dict[str, Any]:
        collector = get_metrics_collector()
        counters = collector.get_counters()
        high = counters.get("confidence.HIGH", 0)
        medium = counters.get("confidence.MEDIUM", 0)
        low = counters.get("confidence.LOW", 0)
        total = high + medium + low
        return {
            "timestamp": self._timestamp(),
            "type": "confidence_distribution",
            "HIGH": {"count": high, "percentage": round(high / max(total, 1) * 100, 2)},
            "MEDIUM": {"count": medium, "percentage": round(medium / max(total, 1) * 100, 2)},
            "LOW": {"count": low, "percentage": round(low / max(total, 1) * 100, 2)},
            "total": total,
        }

    def generate_all_reports(self) -> dict[str, Path]:
        reports = {
            "latency": self.generate_latency_report(),
            "resource": self.generate_resource_report(),
            "errors": self.generate_error_summary(),
            "retries": self.generate_retry_statistics(),
            "confidence": self.generate_confidence_distribution(),
        }
        paths = {}
        for name, data in reports.items():
            path = self.output_dir / f"{name}_report.json"
            with open(path, "w") as f:
                json.dump(data, f, indent=2, default=str)
            paths[name] = path
            logger.info("Generated %s report: %s", name, path)
        return paths

    def generate_csv(self, output_name: str = "system_metrics") -> Path:
        tracker = get_resource_tracker()
        snapshots = list(tracker.snapshots)
        path = self.output_dir / f"{output_name}.csv"
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "cpu_percent", "memory_rss_mb", "memory_percent", "disk_usage_mb", "open_fds"])
            for s in snapshots:
                writer.writerow([
                    s.timestamp, s.cpu_percent, round(s.memory_rss_mb, 2),
                    round(s.memory_percent, 2), round(s.disk_usage_mb, 2), s.open_fds,
                ])
        logger.info("Generated CSV: %s (%d rows)", path, len(snapshots))
        return path
