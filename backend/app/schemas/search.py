from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str


class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    page: int | None = None
    section: str | None = None
    filename: str | None = None
    vector_score: float = 0.0
    bm25_score: float = 0.0
    rerank_score: float = 0.0


class SearchResponse(BaseModel):
    query: str
    confidence: float
    confidence_level: str
    results: list[SearchResultItem]
    latencies: dict[str, float] | None = None
