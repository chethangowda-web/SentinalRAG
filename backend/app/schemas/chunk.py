from pydantic import BaseModel


class ChunkMetadata(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    chunk_text: str
    char_start: int
    char_end: int
    word_count: int
    page_number: int | None
    embedding_status: str


class ChunkListResponse(BaseModel):
    document_id: str
    total_chunks: int
    chunks: list[ChunkMetadata]


class EmbedResponse(BaseModel):
    document_id: str
    total_chunks: int
    embedded_chunks: int
    status: str
