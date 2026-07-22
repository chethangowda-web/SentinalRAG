import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from pathlib import Path

from app.core.database import get_db, get_session_maker
from app.core.exceptions import AppException
from app.models.document import Document
from app.schemas.document import IngestResponse
from app.services.document_service import ingest_document
from app.services.indexing_service import embed_document

logger = logging.getLogger(__name__)

router = APIRouter()

_auto_embed_tasks: set[asyncio.Task] = set()


def _content_type_from_ext(ext: str) -> str:
    mapping = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    return mapping.get(ext, "application/octet-stream")


async def _auto_embed(document_id: str):
    try:
        logger.info("Auto-embed starting for document_id=%s", document_id)
        session_maker = get_session_maker()
        async with session_maker() as bg_db:
            result = await embed_document(document_id, bg_db)
            logger.info("Auto-embed completed for document_id=%s status=%s chunks=%d",
                        document_id, result.status, result.embedded_chunks)
    except Exception as e:
        logger.exception("Auto-embed failed for document_id=%s: %s", document_id, e)


async def _auto_evaluate(document_id: str | None = None):
    try:
        logger.info("Auto-evaluation starting after upload...")
        from evaluation.services.runner import EvaluationRunner
        from evaluation.reports.report_generator import ReportGenerator

        session_maker = get_session_maker()
        async with session_maker() as eval_db:
            eval_id = str(uuid.uuid4())
            runner = EvaluationRunner()

            if document_id:
                questions = await _generate_eval_questions(document_id, eval_db)
                if questions:
                    logger.info("Generated %d document-specific evaluation questions", len(questions))
                else:
                    questions = None

            if questions:
                result = await runner.run(db=eval_db, eval_id=eval_id, questions=questions)
            else:
                dataset_path = str(Path(__file__).resolve().parent.parent.parent.parent / "evaluation" / "datasets" / "benchmark.json")
                result = await runner.run(db=eval_db, dataset_path=dataset_path, eval_id=eval_id)

            report_gen = ReportGenerator()
            report_files = report_gen.generate_all(result)
            logger.info("Auto-evaluation completed eval_id=%s total_questions=%d reports=%s",
                        eval_id, result.get("total_questions", 0), report_files)
    except Exception as e:
        logger.exception("Auto-evaluation failed: %s", e)


async def _generate_eval_questions(document_id: str, db) -> list[dict] | None:
    from sqlalchemy import select
    from app.models.document import Document

    try:
        result = await db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if not doc or not doc.text_content:
            logger.warning("Document %s not found or has no text for eval question generation", document_id)
            return None

        summary = doc.summary or ""
        topics_str = doc.key_topics or ""
        keywords_str = doc.keywords or ""
        topics = [t.strip() for t in topics_str.split(",") if t.strip()] if topics_str else []
        keywords = [k.strip() for k in keywords_str.split(",") if k.strip()] if keywords_str else []
        text_preview = doc.text_content[:2000]

        questions = _generate_questions_from_keywords(topics, keywords, summary, doc.filename)
        if questions:
            return [
                {
                    "id": f"doc-{i}",
                    "question": q,
                    "ground_truth": "",
                    "category": "document_specific",
                    "has_contradiction": False,
                    "needs_clarification": False,
                    "has_context": True,
                }
                for i, q in enumerate(questions)
            ]

        questions = _generate_questions_from_text(doc.filename, text_preview, summary)
        if questions:
            return [
                {
                    "id": f"doc-{i}",
                    "question": q,
                    "ground_truth": "",
                    "category": "document_specific",
                    "has_contradiction": False,
                    "needs_clarification": False,
                    "has_context": True,
                }
                for i, q in enumerate(questions)
            ]

        return None
    except Exception as e:
        logger.warning("Failed to generate evaluation questions for document %s: %s", document_id, e)
        return None


def _generate_questions_from_keywords(topics: list[str], keywords: list[str], summary: str, filename: str) -> list[str]:
    candidates = list(dict.fromkeys(topics + keywords))
    meaningful = [c for c in candidates if len(c) > 3]
    if not meaningful:
        return []

    questions = []
    name = Path(filename).stem.replace("_", " ").replace("-", " ")

    if summary:
        questions.append(f"What is the main topic of the document '{name}'?")
        questions.append(f"Summarize the key points from the document titled '{name}'.")

    for item in meaningful[:4]:
        questions.append(f"What does the document say about {item}?")
        questions.append(f"How is {item} described in the document?")

    if summary:
        questions.append(f"Based on '{name}', what can you tell me about: {summary[:100]}?")

    questions.append(f"What key information is presented in the document '{name}'?")

    return questions[:8]


def _generate_questions_from_text(filename: str, text_preview: str, summary: str) -> list[str]:
    name = Path(filename).stem.replace("_", " ").replace("-", " ")
    words = [w for w in text_preview.lower().split() if len(w) > 5 and w.isalpha()]
    word_freq: dict[str, int] = {}
    for w in words:
        word_freq[w] = word_freq.get(w, 0) + 1
    top_terms = sorted(word_freq, key=word_freq.get, reverse=True)[:6]

    questions = []
    questions.append(f"What is the document '{name}' about?")
    if summary:
        questions.append(f"Can you provide details about: {summary[:120]}?")

    for term in top_terms[:4]:
        questions.append(f"What information does the document provide regarding {term}?")

    questions.append(f"What are the main findings or content in '{name}'?")

    return questions[:8]


@router.post("/ingest", response_model=IngestResponse)
async def upload_document(file: UploadFile | None = None, db: AsyncSession = Depends(get_db)):
    if file is None:
        raise AppException(status_code=400, detail="No file provided. Send a file as multipart/form-data.")

    if not file.filename:
        raise AppException(status_code=400, detail="No file provided")

    filename = file.filename
    ext = Path(filename).suffix.lower()
    content_type = file.content_type or _content_type_from_ext(ext)
    file_bytes = await file.read()

    logger.info("Ingest request: filename=%s content_type=%s size=%d", filename, content_type, len(file_bytes))

    try:
        result = await ingest_document(filename, content_type, file_bytes, db)
    except AppException:
        raise
    except Exception as exc:
        logger.exception("Unhandled error in upload_document")
        raise AppException(status_code=500, detail=f"Unhandled error: {exc}")

    async def _auto_embed_then_eval(doc_id: str):
        await _auto_embed(doc_id)
        await _auto_evaluate(doc_id)

    task = asyncio.create_task(_auto_embed_then_eval(result.document_id))
    _auto_embed_tasks.add(task)
    task.add_done_callback(_auto_embed_tasks.discard)

    return result
