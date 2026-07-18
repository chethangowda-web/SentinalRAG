from pydantic import BaseModel


class IngestResponse(BaseModel):
    document_id: str
    status: str
    pages: int
    words: int
    ocr_used: bool
    processing_time: float
