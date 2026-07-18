import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MetricResult:
    name: str
    value: float
    details: dict[str, Any] | None = None
    success: bool = True
    error: str | None = None


class BaseMetric:
    name: str = "base"
    description: str = "Base metric"

    def compute(self, *args: Any, **kwargs: Any) -> MetricResult:
        raise NotImplementedError

    def __call__(self, *args: Any, **kwargs: Any) -> MetricResult:
        try:
            return self.compute(*args, **kwargs)
        except Exception as e:
            logger.exception("Metric '%s' failed: %s", self.name, e)
            return MetricResult(
                name=self.name,
                value=0.0,
                success=False,
                error=str(e),
            )


@dataclass
class MetricCollection:
    metrics: list[MetricResult] = field(default_factory=list)

    def add(self, result: MetricResult) -> None:
        self.metrics.append(result)

    def to_dict(self) -> dict[str, Any]:
        return {
            m.name: {
                "value": m.value,
                "success": m.success,
                "error": m.error,
                "details": m.details,
            }
            for m in self.metrics
        }

    def get(self, name: str) -> MetricResult | None:
        for m in self.metrics:
            if m.name == name:
                return m
        return None

    @property
    def successful(self) -> list[MetricResult]:
        return [m for m in self.metrics if m.success]

    @property
    def failed(self) -> list[MetricResult]:
        return [m for m in self.metrics if not m.success]
