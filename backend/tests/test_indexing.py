import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import AppException
from app.models.document import Document


@pytest.mark.asyncio
async def test_embed_missing_document(async_client, db_session):
    response = await async_client.post("/api/v1/embed/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_embed_no_text(async_client, db_session):
    doc = Document(
        id="no-text-doc",
        filename="test.pdf",
        file_type="pdf",
        status="processed",
    )
    db_session.add(doc)
    await db_session.commit()

    response = await async_client.post("/api/v1/embed/no-text-doc")
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_chunks_no_document(async_client, db_session):
    response = await async_client.get("/api/v1/document/nonexistent/chunks")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_chunks_empty(async_client, db_session):
    doc = Document(
        id="empty-chunks-doc",
        filename="test.pdf",
        file_type="pdf",
        status="embedded",
    )
    db_session.add(doc)
    await db_session.commit()

    response = await async_client.get("/api/v1/document/empty-chunks-doc/chunks")
    assert response.status_code == 404
