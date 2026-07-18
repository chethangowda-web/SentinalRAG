from pydantic import BaseModel


class MetricSummary(BaseModel):
    count: int
    avg: float
    min: float
    max: float
    p50: float
    p95: float
    p99: float


class PerformanceMetricsResponse(BaseModel):
    latencies: dict[str, MetricSummary]
    counters: dict[str, int]
    errors: dict[str, int | dict[str, int]]


class SystemMetricsResponse(BaseModel):
    cpu: dict[str, float]
    memory: dict[str, float]
    disk: dict[str, float]
    uptime_seconds: int
    samples: int
    duration_seconds: float


class ErrorMetricsResponse(BaseModel):
    total: int
    by_type: dict[str, int]
    by_endpoint: dict[str, int] | None = None


class PerformanceBenchmarkResult(BaseModel):
    operation: str
    avg_ms: float
    min_ms: float
    max_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    samples: int
    success_rate: float


class BenchmarkSuiteResponse(BaseModel):
    suite_name: str
    timestamp: str
    results: list[PerformanceBenchmarkResult]
    summary: dict[str, float]
