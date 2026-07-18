import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MetricSample:
    value: float
    timestamp: float
    tags: dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    def __init__(self, max_samples: int = 10000):
        self.max_samples = max_samples
        self._samples: dict[str, list[MetricSample]] = defaultdict(list)
        self._counters: dict[str, int] = defaultdict(int)
        self._errors: dict[str, int] = defaultdict(int)

    def record(self, metric: str, value: float, **tags: str) -> None:
        samples = self._samples[metric]
        samples.append(MetricSample(value=value, timestamp=time.time(), tags=tags))
        if len(samples) > self.max_samples:
            samples.pop(0)

    def increment(self, counter: str, count: int = 1) -> None:
        self._counters[counter] += count

    def record_error(self, error_type: str) -> None:
        self._errors[error_type] += 1
        self.increment("errors.total")

    def get_metric(self, metric: str) -> list[MetricSample]:
        return list(self._samples.get(metric, []))

    def get_summary(self, metric: str) -> dict[str, float]:
        samples = self._samples.get(metric, [])
        if not samples:
            return {"count": 0, "avg": 0, "min": 0, "max": 0, "p50": 0, "p95": 0, "p99": 0}
        values = sorted(s.value for s in samples)
        n = len(values)
        return {
            "count": n,
            "avg": sum(values) / n,
            "min": values[0],
            "max": values[-1],
            "p50": values[int(n * 0.50)],
            "p95": values[int(n * 0.95)],
            "p99": values[int(n * 0.99)],
        }

    def get_all_metrics(self) -> dict[str, dict[str, float]]:
        return {k: self.get_summary(k) for k in self._samples}

    def get_counters(self) -> dict[str, int]:
        return dict(self._counters)

    def get_errors(self) -> dict[str, Any]:
        return {
            "by_type": dict(self._errors),
            "total": sum(self._errors.values()),
        }

    def get_performance_summary(self) -> dict[str, Any]:
        return {
            "latencies": self.get_all_metrics(),
            "counters": self.get_counters(),
            "errors": self.get_errors(),
        }

    def record_latency(self, operation: str, latency_ms: float, **tags: str) -> None:
        self.record(f"latency.{operation}", latency_ms, **tags)

    def record_component_latency(
        self,
        component: str,
        latency_ms: float,
        success: bool = True,
    ) -> None:
        self.record(f"component.{component}", latency_ms)
        self.increment(f"component_calls.{component}")
        if success:
            self.increment(f"component_success.{component}")
        else:
            self.increment(f"component_failure.{component}")
            self.record_error(f"{component}_failure")


_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector
