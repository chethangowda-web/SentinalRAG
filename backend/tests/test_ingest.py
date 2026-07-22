from pathlib import Path

import pytest

from app.core.exceptions import AppException
from app.services.file_service import validate_file


class TestFileValidation:
    def test_valid_pdf(self):
        validate_file("doc.pdf", "application/pdf", 1024)

    def test_valid_png(self):
        validate_file("image.png", "image/png", 1024)

    def test_valid_jpg(self):
        validate_file("photo.jpg", "image/jpeg", 1024)

    def test_valid_jpeg(self):
        validate_file("photo.jpeg", "image/jpeg", 1024)

    def test_invalid_extension(self):
        with pytest.raises(AppException) as exc:
            validate_file("file.txt", "text/plain", 1024)
        assert exc.value.status_code == 400

    def test_invalid_content_type(self):
        with pytest.raises(AppException) as exc:
            validate_file("doc.pdf", "application/xml", 1024)
        assert exc.value.status_code == 415

    def test_file_too_large(self, monkeypatch):
        monkeypatch.setattr("app.core.config.settings.MAX_FILE_SIZE", 100)
        with pytest.raises(AppException) as exc:
            validate_file("doc.pdf", "application/pdf", 200)
        assert exc.value.status_code == 413
        assert "too large" in exc.value.detail.lower()


class TestIngestAPI:
    @pytest.mark.asyncio
    async def test_upload_no_file(self, async_client):
        response = await async_client.post("/api/v1/ingest")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_invalid_extension(self, async_client):
        response = await async_client.post(
            "/api/v1/ingest",
            files={"file": ("test.txt", b"hello world", "text/plain")},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_valid_pdf(self, async_client, db_session, monkeypatch):
        monkeypatch.setattr("app.core.config.settings.TEXT_MIN_LENGTH_FOR_PDF", 1)
        pdf_path = Path(__file__).parent / "fixtures" / "test.pdf"
        pdf_bytes = pdf_path.read_bytes()
        response = await async_client.post(
            "/api/v1/ingest",
            files={"file": ("test.pdf", pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"
        assert data["pages"] == 1
        assert data["words"] > 0
        assert data["ocr_used"] is False
        assert "document_id" in data
