"""Load the benchmark's sample documents into a user's account so the benchmark is meaningful.

The 18 benchmark questions are about six small policy documents (backend/evaluation/corpus/).
Running them against someone's unrelated uploads measures nothing, so the evaluation page first
asks the user to load these documents (a few seconds, six small PDFs), then runs the benchmark.
"""
import asyncio
import logging
import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.services.document_service import ingest_document
from app.services.indexing_service import schedule_embedding
from app.utils.file_utils import get_upload_path

logger = logging.getLogger(__name__)

CORPUS_DIR = Path(__file__).resolve().parents[2] / "evaluation" / "corpus"

_loading_users: set[str] = set()
_background_tasks: set[asyncio.Task] = set()


def corpus_filenames() -> list[str]:
    return sorted(p.name for p in CORPUS_DIR.glob("*.pdf"))


async def benchmark_status(db: AsyncSession, user_id: str) -> dict:
    wanted = corpus_filenames()
    rows = (await db.execute(
        select(Document.filename, Document.status).where(Document.user_id == user_id, Document.filename.in_(wanted))
    )).all()
    by_name: dict[str, str] = {}
    for filename, status in rows:
        # If a name was uploaded twice, the best status wins
        if by_name.get(filename) != "embedded":
            by_name[filename] = status

    documents = [{"filename": name, "status": by_name.get(name, "missing")} for name in wanted]
    return {
        "ready": bool(wanted) and all(d["status"] == "embedded" for d in documents),
        "loading": user_id in _loading_users or any(d["status"] in ("processed", "embedding") for d in documents),
        "documents": documents,
    }


async def _load_for_user(user_id: str) -> None:
    from app.core.database import get_session_maker

    try:
        async with get_session_maker()() as db:
            existing = {
                name for (name,) in (await db.execute(
                    select(Document.filename).where(Document.user_id == user_id, Document.filename.in_(corpus_filenames()))
                )).all()
            }
        for name in corpus_filenames():
            if name in existing:
                continue
            upload_path, _ = get_upload_path(name)
            shutil.copyfile(CORPUS_DIR / name, upload_path)  # ingest_document consumes (deletes) this copy
            async with get_session_maker()() as db:
                result = await ingest_document(name, "application/pdf", upload_path, upload_path.stat().st_size if upload_path.exists() else 0, db, user_id=user_id)
            schedule_embedding(result.document_id, user_id)
        # Documents that already existed but were never indexed
        async with get_session_maker()() as db:
            stale = (await db.execute(
                select(Document.id).where(Document.user_id == user_id, Document.filename.in_(corpus_filenames()), Document.status.in_(("processed", "failed")))
            )).scalars().all()
        for doc_id in stale:
            schedule_embedding(doc_id, user_id)
    except Exception:
        logger.exception("Loading the benchmark documents failed for user %s", user_id)
    finally:
        _loading_users.discard(user_id)


def start_loading(user_id: str) -> bool:
    """Begin loading the sample documents in the background. False if a load is already running."""
    if user_id in _loading_users:
        return False
    _loading_users.add(user_id)
    task = asyncio.create_task(_load_for_user(user_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return True
