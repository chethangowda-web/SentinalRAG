from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: int | None = None


class ComponentStatus(BaseModel):
    status: str
    error: str | None = None
    model: str | None = None


class ReadinessResponse(BaseModel):
    ready: bool
    database: ComponentStatus | dict
    qdrant: ComponentStatus | dict
    ocr: ComponentStatus | dict
    embedding: ComponentStatus | dict
    llm: ComponentStatus | dict


class DiskUsage(BaseModel):
    upload_dir_mb: float | None = None
    processed_dir_mb: float | None = None
    total_mb: float | None = None
    error: str | None = None


class MemoryUsage(BaseModel):
    total_mb: float | None = None
    available_mb: float | None = None
    used_mb: float | None = None
    percent: float | None = None
    note: str | None = None
    error: str | None = None


class MetricsResponse(BaseModel):
    version: str
    uptime_seconds: int
    database: ComponentStatus | dict
    qdrant: ComponentStatus | dict
    ocr: ComponentStatus | dict
    embedding: ComponentStatus | dict
    llm: ComponentStatus | dict
    disk: DiskUsage | dict
    memory: MemoryUsage | dict
