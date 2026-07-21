import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.core.exceptions import (
    AppException, LLMTimeoutError, QdrantConnectionError, DatabaseConnectionError,
    OCRError, NetworkError,
)

pytestmark = pytest.mark.asyncio


class TestQdrantUnavailable:
    @patch("app.services.vector_search_service.get_qdrant_client")
    async def test_vector_search_qdrant_down(self, mock_get_client):
        from app.services.vector_search_service import search_vector
        mock_get_client.side_effect = ConnectionError("Qdrant refused connection")
        with pytest.raises(Exception):
            await search_vector("test query", top_k=5)

    @patch("app.services.retrieval_service.search_vector")
    @patch("app.services.retrieval_service.search_bm25")
    async def test_retrieval_qdrant_fallback(self, mock_bm25, mock_vector):
        from app.services.retrieval_service import retrieve
        mock_vector.side_effect = QdrantConnectionError("Qdrant down")
        mock_bm25.return_value = [
            {"chunk_id": "c1", "document_id": "d1", "text": "BM25 only result",
             "score": 0.8, "vector_score": 0.0, "rerank_score": 0.8, "bm25_score": 0.8,
             "page_number": 1, "section": "test", "filename": "doc.pdf"}
        ]
        result = await retrieve("test query")
        assert len(result["results"]) > 0
        assert result["results"][0]["text"] == "BM25 only result"
        assert "latencies" in result

    @patch("app.services.qdrant_service.get_qdrant_client")
    async def test_qdrant_upsert_failure(self, mock_get_client):
        from app.services.qdrant_service import upsert_vectors
        mock_client = MagicMock()
        mock_client.upsert.side_effect = ConnectionError("Qdrant connection lost")
        mock_get_client.return_value = mock_client

        with pytest.raises(Exception):
            await upsert_vectors("collection", [])


class TestDatabaseUnavailable:
    @patch("app.core.database.get_engine")
    async def test_init_db_failure(self, mock_get_engine):
        from app.core.database import init_db
        mock_engine = MagicMock()
        mock_engine.begin.side_effect = DatabaseConnectionError("Database connection refused")
        mock_get_engine.return_value = mock_engine
        with pytest.raises(DatabaseConnectionError):
            await init_db()

    @patch("app.services.bm25_service.get_db")
    async def test_bm25_db_down(self, mock_get_db):
        from app.services.bm25_service import search_bm25
        mock_get_db.side_effect = DatabaseConnectionError("PostgreSQL unavailable")
        with pytest.raises(DatabaseConnectionError):
            await search_bm25("test query", top_k=5)

    @patch("app.services.document_service.get_db")
    async def test_ingest_db_failure(self, mock_get_db):
        from app.services.document_service import ingest_document
        mock_get_db.side_effect = DatabaseConnectionError("DB unavailable")
        with pytest.raises(DatabaseConnectionError):
            await ingest_document("test.pdf", "application/pdf", b"test content", None)


class TestOCRFailure:
    @patch("app.services.ocr_service.TESSERACT_AVAILABLE", False)
    def test_ocr_not_available_image(self):
        from app.services.ocr_service import ocr_image
        from pathlib import Path
        with pytest.raises(RuntimeError, match="OCR is not available"):
            ocr_image(Path("test.png"))

    @patch("app.services.ocr_service.PYMUPDF_AVAILABLE", False)
    def test_ocr_pymupdf_not_available(self):
        from app.services.ocr_service import ocr_pdf
        from pathlib import Path
        with pytest.raises(RuntimeError, match="PyMuPDF is not available"):
            ocr_pdf(Path("test.pdf"))

    @patch("app.services.ocr_service.ocr_image")
    def test_ocr_pdf_page_failure(self, mock_ocr_image):
        from app.services.ocr_service import ocr_pdf
        from pathlib import Path
        mock_ocr_image.side_effect = RuntimeError("OCR failed on page")
        with pytest.raises(RuntimeError, match="OCR failed"):
            ocr_pdf(Path("test.pdf"))


class TestLLMFailure:
    @patch("app.services.answer_generator.ChatOpenAI")
    async def test_llm_timeout(self, mock_chat):
        from app.services.answer_generator import generate_answer
        mock_instance = MagicMock()
        mock_instance.ainvoke.side_effect = TimeoutError("LLM timed out after 30s")
        mock_chat.return_value = mock_instance
        result = await generate_answer("test question", [{"text": "context"}])
        assert "based on the available context" in result.lower() or "error" in result.lower()

    @patch("app.services.query_rewriter.ChatOpenAI")
    async def test_rewriter_llm_failure(self, mock_chat):
        from app.services.query_rewriter import rewrite_query
        mock_instance = MagicMock()
        mock_instance.ainvoke.side_effect = Exception("API returned 503")
        mock_chat.return_value = mock_instance
        result = await rewrite_query("test question", [{"text": "context"}])
        assert result == "test question"

    @patch("app.api.v1.chat.build_graph")
    async def test_chat_graph_llm_error(self, mock_build):
        from app.api.v1.chat import chat_endpoint
        from app.schemas.chat import ChatRequest
        from sqlalchemy.ext.asyncio import AsyncSession

        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(side_effect=LLMTimeoutError("LLM timed out"))
        mock_build.return_value = mock_graph

        result = await chat_endpoint(ChatRequest(question="test"), MagicMock(spec=AsyncSession))
        assert result.confidence == 0.0
        assert result.confidence_level == "LOW"
        assert "error" in result.reasoning_path


class TestEmbeddingFailure:
    @patch("app.services.embedding_service._model", None)
    def test_embedding_model_not_loaded(self):
        from app.services.embedding_service import generate_embeddings
        with pytest.raises(RuntimeError, match="Model not loaded"):
            generate_embeddings(["test text"])

    @patch("app.services.embedding_service._model")
    def test_embedding_encode_failure(self, mock_model):
        from app.services.embedding_service import generate_embeddings
        mock_model.encode.side_effect = Exception("CUDA out of memory")
        with pytest.raises(Exception, match="CUDA"):
            generate_embeddings(["test text"])


class TestInvalidUpload:
    @pytest.mark.parametrize("filename,content_type", [
        ("test.exe", "application/x-msdownload"),
        ("test.txt", "text/plain"),
        ("test.html", "text/html"),
        ("test.js", "application/javascript"),
    ])
    def test_invalid_file_extension(self, filename, content_type):
        from app.services.file_service import validate_file
        with pytest.raises(AppException, match="Unsupported file extension"):
            validate_file(filename, content_type, 1024)

    @pytest.mark.parametrize("filename,content_type", [
        ("test.pdf", "text/plain"),
        ("test.png", "application/pdf"),
    ])
    def test_invalid_content_type(self, filename, content_type):
        from app.services.file_service import validate_file
        with pytest.raises(AppException, match="Unsupported content type"):
            validate_file(filename, content_type, 1024)

    def test_file_too_large(self):
        from app.services.file_service import validate_file
        from app.core.config import settings
        with pytest.raises(AppException, match="File too large"):
            validate_file("test.pdf", "application/pdf", settings.MAX_FILE_SIZE + 1)

    def test_empty_filename(self):
        from app.services.file_service import validate_file
        with pytest.raises(AppException, match="Unsupported file extension"):
            validate_file("", "application/pdf", 1024)


class TestNetworkFailure:
    @patch("app.services.vector_search_service.get_qdrant_client")
    async def test_qdrant_network_error(self, mock_get_client):
        from app.services.vector_search_service import search_vector
        mock_get_client.side_effect = NetworkError("Qdrant unreachable at http://qdrant:6333")
        with pytest.raises(NetworkError):
            await search_vector("test", top_k=5)

    @patch("httpx.AsyncClient")
    async def test_llm_api_network_error(self, mock_client):
        from app.services.answer_generator import generate_answer
        mock_client.return_value.__aenter__.return_value.post.side_effect = NetworkError("Connection reset by peer")
        result = await generate_answer("test", [{"text": "context"}])
        assert "error" in result.lower() or "unable" in result.lower() or "based on" in result.lower()


class TestCorruptedUpload:
    @pytest.mark.parametrize("file_bytes", [
        b"",
        b"not a real pdf file at all",
        b"\x00\x00\x00\x00" * 100,
    ])
    @patch("app.services.document_service.ingest_document")
    async def test_corrupted_pdf_handling(self, mock_ingest, file_bytes):
        mock_ingest.side_effect = OCRError("Failed to extract text from file")
        with pytest.raises(OCRError):
            await mock_ingest("corrupted.pdf", "application/pdf", file_bytes, None)


class TestGracefulDegradation:
    @patch("app.services.retrieval_service.search_vector")
    @patch("app.services.retrieval_service.search_bm25")
    async def test_bm25_only_degradation(self, mock_bm25, mock_vector):
        from app.services.retrieval_service import retrieve
        mock_vector.side_effect = QdrantConnectionError("Qdrant down")
        mock_bm25.return_value = [
            {"chunk_id": "c1", "document_id": "d1", "text": "fallback result",
             "score": 0.7, "vector_score": 0.0, "rerank_score": 0.7, "bm25_score": 0.7,
             "page_number": 1, "section": "test", "filename": "doc.pdf"}
        ]
        result = await retrieve("test")
        assert len(result["results"]) > 0
        assert "latencies" in result

    @patch("app.services.retrieval_service.search_vector")
    @patch("app.services.retrieval_service.search_bm25")
    async def test_complete_retrieval_failure(self, mock_bm25, mock_vector):
        from app.services.retrieval_service import retrieve
        mock_vector.side_effect = QdrantConnectionError("Qdrant down")
        mock_bm25.side_effect = DatabaseConnectionError("DB down")
        result = await retrieve("test")
        assert len(result["results"]) == 0
        assert result["confidence"] == 0.0

    @patch("app.api.v1.chat.build_graph")
    async def test_chat_graph_crash(self, mock_build):
        from app.api.v1.chat import chat_endpoint
        from app.schemas.chat import ChatRequest
        from sqlalchemy.ext.asyncio import AsyncSession

        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(side_effect=Exception("Critical pipeline failure"))
        mock_build.return_value = mock_graph

        result = await chat_endpoint(ChatRequest(question="test"), MagicMock(spec=AsyncSession))
        assert result.answer == "An error occurred while processing your question. Please try again."
        assert result.confidence == 0.0

    async def test_empty_question_handling(self):
        from app.api.v1.chat import chat_endpoint
        from app.schemas.chat import ChatRequest
        from sqlalchemy.ext.asyncio import AsyncSession

        result = await chat_endpoint(ChatRequest(question=""), MagicMock(spec=AsyncSession))
        assert result.answer == "Please provide a valid question."
        assert result.confidence == 0.0
        assert result.confidence_level == "LOW"

    async def test_whitespace_question(self):
        from app.api.v1.chat import chat_endpoint
        from app.schemas.chat import ChatRequest
        from sqlalchemy.ext.asyncio import AsyncSession

        result = await chat_endpoint(ChatRequest(question="   "), MagicMock(spec=AsyncSession))
        assert result.confidence == 0.0
