import pytest

from app.models.document import Document


@pytest.mark.asyncio
async def test_embed_missing_document(async_client, db_session):
    response = await async_client.post("/api/v1/embed/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_embed_no_text(async_client, db_session, test_user):
    doc = Document(
        id="no-text-doc",
        filename="test.pdf",
        file_type="pdf",
        status="processed",
        user_id=test_user.id,
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
async def test_list_chunks_empty(async_client, db_session, test_user):
    doc = Document(
        id="empty-chunks-doc",
        filename="test.pdf",
        file_type="pdf",
        status="embedded",
        user_id=test_user.id,
    )
    db_session.add(doc)
    await db_session.commit()

    response = await async_client.get("/api/v1/document/empty-chunks-doc/chunks")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_embed_other_users_document_is_not_found(async_client, db_session):
    doc = Document(
        id="someone-elses-doc",
        filename="test.pdf",
        file_type="pdf",
        status="processed",
        text_content="private text",
        user_id="another-user-id",
    )
    db_session.add(doc)
    await db_session.commit()

    response = await async_client.post("/api/v1/embed/someone-elses-doc")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_chunks_other_users_document_is_not_found(async_client, db_session):
    doc = Document(
        id="someone-elses-chunks-doc",
        filename="test.pdf",
        file_type="pdf",
        status="embedded",
        user_id="another-user-id",
    )
    db_session.add(doc)
    await db_session.commit()

    response = await async_client.get("/api/v1/document/someone-elses-chunks-doc/chunks")
    assert response.status_code == 404
