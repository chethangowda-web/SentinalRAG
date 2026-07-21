import logging
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.models.document import Document
from app.models.chunk import Chunk
from app.services.qdrant_service import delete_document_vectors

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "status": d.status,
            "pages": d.pages,
            "word_count": d.word_count,
            "char_count": d.char_count,
            "ocr_used": d.ocr_used,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "updated_at": d.updated_at.isoformat() if d.updated_at else None,
            "file_size": d.file_size,
            "processing_time": d.processing_time,
        }
        for d in docs
    ]


@router.get("/documents/{document_id}")
async def get_document(document_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise AppException(status_code=404, detail=f"Document {document_id} not found")
    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "status": doc.status,
        "pages": doc.pages,
        "word_count": doc.word_count,
        "char_count": doc.char_count,
        "ocr_used": doc.ocr_used,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
        "file_size": doc.file_size,
        "processing_time": doc.processing_time,
        "original_path": doc.original_path,
        "extracted_text_path": doc.extracted_text_path,
        "text_content": doc.text_content,
    }


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise AppException(status_code=404, detail=f"Document {document_id} not found")

    # Delete Qdrant vectors if they exist
    try:
        delete_document_vectors(document_id)
    except Exception as e:
        logger.warning("Failed to delete Qdrant vectors for %s: %s", document_id, e)

    # Delete files from disk
    for path_str in [doc.original_path, doc.extracted_text_path]:
        if path_str:
            p = Path(path_str)
            if p.exists():
                p.unlink(missing_ok=True)

    # Delete chunks (cascade should handle this, but be explicit)
    await db.execute(delete(Chunk).where(Chunk.document_id == document_id))

    # Delete document
    await db.delete(doc)
    await db.commit()

    logger.info("Document deleted: %s (%s)", doc.filename, document_id)
    return {"status": "deleted", "document_id": document_id}
