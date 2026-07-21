from pydantic import BaseModel


class IngestResponse(BaseModel):
    document_id: str
    status: str
    pages: int
    words: int
    ocr_used: bool
    processing_time: float
    ocr_quality: str | None = None
    ocr_confidence: float | None = None
    summary: str | None = None
    document_type: str | None = None
    estimated_reading_time: int | None = None
    is_duplicate: bool = False
    duplicate_info: dict | None = None
