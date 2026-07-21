import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.document import Document
from app.models.chunk import Chunk
from app.models.chat_session import ChatSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    doc_count_result = await db.execute(select(func.count(Document.id)))
    total_docs = doc_count_result.scalar() or 0

    chunk_count_result = await db.execute(select(func.count(Chunk.id)))
    total_chunks = chunk_count_result.scalar() or 0

    session_count_result = await db.execute(select(func.count(ChatSession.id)))
    total_sessions = session_count_result.scalar() or 0

    doc_by_status_result = await db.execute(
        select(Document.status, func.count(Document.id)).group_by(Document.status)
    )
    docs_by_status = {row[0]: row[1] for row in doc_by_status_result.all()}

    total_chars_result = await db.execute(
        select(func.coalesce(func.sum(Document.char_count), 0))
    )
    total_chars = total_chars_result.scalar() or 0

    total_words_result = await db.execute(
        select(func.coalesce(func.sum(Document.word_count), 0))
    )
    total_words = total_words_result.scalar() or 0

    total_pages_result = await db.execute(
        select(func.coalesce(func.sum(Document.pages), 0))
    )
    total_pages = total_pages_result.scalar() or 0

    avg_ocr_conf_result = await db.execute(
        select(func.avg(Document.ocr_confidence)).where(Document.ocr_confidence.isnot(None))
    )
    avg_ocr_conf = avg_ocr_conf_result.scalar()

    doc_types_result = await db.execute(
        select(Document.document_type, func.count(Document.id)).where(Document.document_type.isnot(None)).group_by(Document.document_type)
    )
    doc_types = {row[0]: row[1] for row in doc_types_result.all()}

    recent_result = await db.execute(
        select(Document.id, Document.filename, Document.created_at, Document.document_type, Document.ocr_quality)
        .order_by(Document.created_at.desc())
        .limit(5)
    )
    recent_docs = [
        {
            "id": row.id,
            "filename": row.filename,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "document_type": row.document_type,
            "ocr_quality": row.ocr_quality,
        }
        for row in recent_result.all()
    ]

    return {
        "total_documents": total_docs,
        "total_chunks": total_chunks,
        "total_sessions": total_sessions,
        "docs_by_status": docs_by_status,
        "total_chars": total_chars,
        "total_words": total_words,
        "total_pages": total_pages,
        "avg_ocr_confidence": round(avg_ocr_conf, 1) if avg_ocr_conf else None,
        "document_types": doc_types,
        "recent_documents": recent_docs,
    }


@router.get("/dashboard/daily-stats")
async def get_daily_stats(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import cast, Date

    daily_counts = await db.execute(
        select(
            cast(Document.created_at, Date).label("date"),
            func.count(Document.id).label("count"),
        )
        .group_by(cast(Document.created_at, Date))
        .order_by(cast(Document.created_at, Date).desc())
        .limit(14)
    )
    return [
        {"date": str(row.date), "documents": row.count}
        for row in daily_counts.all()
    ]
