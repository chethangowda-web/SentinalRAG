import asyncio
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.chunk import Chunk
from app.models.document import Document
from app.services import indexing_service
from app.services.indexing_service import recover_interrupted_indexing, schedule_embedding


def _doc(doc_id: str, status: str, user_id: str | None) -> Document:
    return Document(id=doc_id, filename=f"{doc_id}.pdf", file_type="pdf", status=status, user_id=user_id)


@pytest.mark.asyncio
async def test_reindex_schedules_a_failed_document(async_client, db_session, test_user):
    db_session.add(_doc("failed-doc", "failed", test_user.id))
    await db_session.commit()
    with patch("app.api.v1.documents.schedule_embedding") as schedule:
        r = await async_client.post("/api/v1/documents/failed-doc/reindex")
    assert r.status_code == 202 and r.json() == {"status": "embedding"}
    schedule.assert_called_once_with("failed-doc", test_user.id)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["embedding", "embedded"])
async def test_reindex_does_nothing_when_indexed_or_in_progress(async_client, db_session, test_user, status):
    db_session.add(_doc("busy", status, test_user.id))
    await db_session.commit()
    with patch("app.api.v1.documents.schedule_embedding") as schedule:
        r = await async_client.post("/api/v1/documents/busy/reindex")
    assert r.json() == {"status": status}
    schedule.assert_not_called()


@pytest.mark.asyncio
async def test_reindex_of_another_users_document_is_not_found(async_client, db_session):
    db_session.add(_doc("theirs", "failed", "another-user-id"))
    await db_session.commit()
    with patch("app.api.v1.documents.schedule_embedding") as schedule:
        r = await async_client.post("/api/v1/documents/theirs/reindex")
    assert r.status_code == 404
    schedule.assert_not_called()


@pytest.mark.asyncio
async def test_document_detail_reports_its_chunk_count(async_client, db_session, test_user):
    db_session.add(_doc("with-chunks", "embedded", test_user.id))
    for i in range(3):
        db_session.add(Chunk(id=f"c{i}", document_id="with-chunks", chunk_index=i, chunk_text="t", char_start=0, char_end=1, word_count=1))
    await db_session.commit()
    detail = (await async_client.get("/api/v1/documents/with-chunks")).json()
    assert detail["chunk_count"] == 3 and detail["status"] == "embedded"


@pytest.mark.asyncio
async def test_restart_marks_interrupted_indexing_as_failed(db_session, test_user):
    db_session.add(_doc("was-embedding", "embedding", test_user.id))
    db_session.add(_doc("done", "embedded", test_user.id))
    await db_session.commit()

    assert await recover_interrupted_indexing(db_session) == 1

    statuses = {d.id: d.status for d in (await db_session.execute(select(Document))).scalars().all()}
    assert statuses == {"was-embedding": "failed", "done": "embedded"}


@pytest.mark.asyncio
async def test_documents_are_indexed_one_at_a_time_and_failures_do_not_leak():
    running = 0
    peak = 0

    async def fake_embed(document_id, db, user_id=None):
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.02)
        running -= 1
        if document_id == "boom":
            raise RuntimeError("embedding failed")

    class _Session:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *exc):
            return False

    with patch.object(indexing_service, "embed_document", fake_embed), \
            patch("app.core.database.get_session_maker", lambda: (lambda: _Session())):
        for doc_id in ("a", "boom", "b"):
            schedule_embedding(doc_id, "u")
        await asyncio.gather(*list(indexing_service._background_tasks))

    assert peak == 1  # the semaphore serialises indexing
    assert not indexing_service._background_tasks  # finished tasks are released


def test_auto_evaluation_is_opt_in():
    assert settings.AUTO_EVALUATE_ON_UPLOAD is False
