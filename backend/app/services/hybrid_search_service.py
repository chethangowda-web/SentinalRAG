import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

RRF_K = 60


class HybridResult:
    def __init__(
        self,
        chunk_id: str,
        document_id: str,
        text: str,
        vector_score: float = 0.0,
        bm25_score: float = 0.0,
        rrf_score: float = 0.0,
        page_number: int | None = None,
        section: str | None = None,
        filename: str | None = None,
        chunk_index: int | None = None,
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.text = text
        self.vector_score = vector_score
        self.bm25_score = bm25_score
        self.rrf_score = rrf_score
        self.page_number = page_number
        self.section = section
        self.filename = filename
        self.chunk_index = chunk_index


def fuse_results(
    vector_results: list[Any],
    bm25_results: list[Any],
    top_k: int = 20,
) -> list[HybridResult]:
    start = time.perf_counter()

    rank_scores: dict[str, dict] = {}

    for rank, vr in enumerate(vector_results):
        cid = vr.chunk_id
        if cid not in rank_scores:
            rank_scores[cid] = {
                "chunk_id": cid,
                "document_id": vr.document_id,
                "text": vr.text,
                "vector_score": vr.score,
                "bm25_score": 0.0,
                "page_number": vr.page_number,
                "section": vr.section,
                "filename": vr.filename,
                "chunk_index": vr.chunk_index,
                "rrf_score": 0.0,
            }
        rank_scores[cid]["vector_score"] = max(rank_scores[cid]["vector_score"], vr.score)
        rank_scores[cid]["rrf_score"] += 1.0 / (RRF_K + rank + 1)

    for rank, br in enumerate(bm25_results):
        cid = br.chunk_id
        if cid not in rank_scores:
            rank_scores[cid] = {
                "chunk_id": cid,
                "document_id": br.document_id,
                "text": br.text,
                "vector_score": 0.0,
                "bm25_score": br.score,
                "page_number": br.page_number,
                "section": br.section,
                "filename": br.filename,
                "chunk_index": br.chunk_index,
                "rrf_score": 0.0,
            }
        else:
            rank_scores[cid]["bm25_score"] = max(rank_scores[cid]["bm25_score"], br.score)
            rank_scores[cid]["section"] = rank_scores[cid]["section"] or br.section
        rank_scores[cid]["rrf_score"] += 1.0 / (RRF_K + rank + 1)

    sorted_results = sorted(
        rank_scores.values(),
        key=lambda x: x["rrf_score"],
        reverse=True,
    )[:top_k]

    fused: list[HybridResult] = []
    for item in sorted_results:
        fused.append(HybridResult(
            chunk_id=item["chunk_id"],
            document_id=item["document_id"],
            text=item["text"],
            vector_score=item["vector_score"],
            bm25_score=item["bm25_score"],
            rrf_score=round(item["rrf_score"], 6),
            page_number=item["page_number"],
            section=item["section"],
            filename=item["filename"],
            chunk_index=item["chunk_index"],
        ))

    elapsed = round((time.perf_counter() - start) * 1000, 1)
    logger.info(
        "RRF fusion: %.1fms vector=%d bm25=%d merged=%d returned=%d",
        elapsed, len(vector_results), len(bm25_results), len(rank_scores), len(fused),
    )

    return fused
