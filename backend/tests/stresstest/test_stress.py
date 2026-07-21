import time
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

pytestmark = pytest.mark.asyncio


class TestLargeDocumentStress:
    @pytest.mark.timeout(60)
    def test_large_text_cleaning(self):
        from app.services.text_cleaning import clean_text
        text = "\n".join([
            f"Page {p}\nHeader Section\n" + "normal content. " * 500 + "\nFooter Section\n"
            for p in range(100)
        ])
        start = time.perf_counter()
        result = clean_text(text)
        elapsed = (time.perf_counter() - start) * 1000
        assert len(result) > 0
        assert elapsed < 10000, f"Cleaning 100 pages took {elapsed:.1f}ms (limit 10000ms)"

    @pytest.mark.timeout(60)
    def test_chunking_thousands_of_chunks(self):
        from app.services.chunking_service import chunk_text
        text = "\n\n".join([f"Section {i}. " + "content words " * 200 for i in range(500)])
        start = time.perf_counter()
        chunks = chunk_text(text)
        elapsed = (time.perf_counter() - start) * 1000
        assert len(chunks) > 100
        assert elapsed < 15000, f"Chunking 500 sections took {elapsed:.1f}ms (limit 15000ms)"

    @pytest.mark.timeout(60)
    def test_embedding_normalize_thousands(self):
        from app.services.embedding_service import normalize_embedding
        import time

        vectors = [[0.1 * ((i + j) % 10) for i in range(384)] for j in range(1000)]
        start = time.perf_counter()
        for v in vectors:
            normalize_embedding(v)
        elapsed = (time.perf_counter() - start) * 1000
        assert elapsed < 5000, f"Normalizing 1000 vectors took {elapsed:.1f}ms (limit 5000ms)"


class TestRapidUploadStress:
    @patch("app.services.file_service.validate_file")
    @patch("app.services.file_service.save_upload")
    @pytest.mark.timeout(30)
    def test_rapid_file_validation(self, mock_save, mock_validate):
        from app.services.file_service import validate_file
        import time

        files = [
            (f"test_{i}.pdf", "application/pdf", 1024 * 1024)
            for i in range(100)
        ]
        start = time.perf_counter()
        for fname, ctype, fsize in files:
            validate_file(fname, ctype, fsize)
        elapsed = (time.perf_counter() - start) * 1000
        assert elapsed < 500, f"100 file validations took {elapsed:.1f}ms (limit 500ms)"


class TestConcurrentChunkingStress:
    @pytest.mark.timeout(60)
    @pytest.mark.parametrize("concurrent", [1, 5, 10])
    def test_concurrent_chunking(self, concurrent):
        from app.services.chunking_service import chunk_text
        import asyncio
        import time

        async def run_concurrent():
            texts = [
                "\n\n".join([f"Para {i}. " + "content " * 100 for i in range(20)])
                for _ in range(concurrent)
            ]
            start = time.perf_counter()
            results = await asyncio.gather(*[
                asyncio.to_thread(chunk_text, text) for text in texts
            ])
            elapsed = (time.perf_counter() - start) * 1000
            return results, elapsed

        results, elapsed = asyncio.run(run_concurrent())
        assert all(len(r) > 0 for r in results)
        limit = 5000 * concurrent
        assert elapsed < limit, f"{concurrent} concurrent chunking took {elapsed:.1f}ms (limit {limit}ms)"

    @pytest.mark.timeout(60)
    @pytest.mark.parametrize("concurrent", [1, 5, 10])
    def test_concurrent_text_cleaning(self, concurrent):
        from app.services.text_cleaning import clean_text
        import asyncio
        import time

        async def run_concurrent():
            texts = [
                "\n".join([f"Page {p}\ncontent. " * 50 for p in range(10)])
                for _ in range(concurrent)
            ]
            start = time.perf_counter()
            results = await asyncio.gather(*[
                asyncio.to_thread(clean_text, text) for text in texts
            ])
            elapsed = (time.perf_counter() - start) * 1000
            return results, elapsed

        results, elapsed = asyncio.run(run_concurrent())
        assert all(len(r) > 0 for r in results)
        limit = 3000 * concurrent
        assert elapsed < limit, f"{concurrent} concurrent cleaning took {elapsed:.1f}ms (limit {limit}ms)"


class TestHighVolumeStress:
    def test_hybrid_fusion_large_result_sets(self):
        from app.services.hybrid_search_service import fuse_results
        import time

        vector_results = [
            {"chunk_id": f"v_{i}", "document_id": "doc1", "text": f"text {i}", "score": 0.99 - i * 0.0001,
             "page_number": i, "section": "test"}
            for i in range(500)
        ]
        bm25_results = [
            {"chunk_id": f"b_{i}", "document_id": "doc1", "text": f"text {i}", "score": 0.98 - i * 0.0001,
             "page_number": i, "section": "test"}
            for i in range(500)
        ]
        start = time.perf_counter()
        result = fuse_results(vector_results, bm25_results, top_k=50)
        elapsed = (time.perf_counter() - start) * 1000
        assert len(result) <= 50
        assert elapsed < 500, f"RRF fusion of 1000 results took {elapsed:.1f}ms (limit 500ms)"

    def test_confidence_scaling(self):
        from app.services.confidence_service import calculate_confidence
        import time

        chunk_scores = [
            {"vector_score": 0.9 - i * 0.01, "rerank_score": 0.92 - i * 0.01}
            for i in range(100)
        ]
        start = time.perf_counter()
        for _ in range(100):
            calculate_confidence(chunk_scores)
        elapsed = (time.perf_counter() - start) * 1000
        assert elapsed < 200, f"100 confidence calculations took {elapsed:.1f}ms (limit 200ms)"


class TestRapidApiStress:
    @patch("app.api.v1.chat.build_graph")
    @pytest.mark.timeout(30)
    async def test_rapid_chat_api(self, mock_build):
        from app.api.v1.chat import chat_endpoint, ChatRequest

        from sqlalchemy.ext.asyncio import AsyncSession

        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "answer": "test answer",
            "confidence_score": 92.5,
            "confidence_level": "HIGH",
            "reasoning_path": ["retrieve", "generate"],
            "citations": [],
            "clarification_question": None,
            "latencies": {"total": 100},
        })
        mock_build.return_value = mock_graph

        request = ChatRequest(question="What is the revenue?")
        import time
        start = time.perf_counter()
        for i in range(10):
            await chat_endpoint(request, MagicMock(spec=AsyncSession))
        elapsed = (time.perf_counter() - start) * 1000
        assert elapsed < 2000, f"10 rapid chat calls took {elapsed:.1f}ms (limit 2000ms)"

    @patch("app.api.v1.ingest.ingest_document")
    @pytest.mark.timeout(30)
    async def test_rapid_ingest_api(self, mock_ingest):
        from app.api.v1.ingest import upload_document
        from fastapi import UploadFile
        from io import BytesIO

        mock_ingest.return_value = {
            "document_id": "test-id",
            "status": "completed",
            "pages": 10,
            "words": 5000,
            "ocr_used": False,
            "processing_time": 1.5,
        }

        import time
        start = time.perf_counter()
        for i in range(10):
            file = UploadFile(filename=f"test_{i}.pdf", file=BytesIO(b"test content"), content_type="application/pdf")
            await upload_document(file, MagicMock())
        elapsed = (time.perf_counter() - start) * 1000
        assert elapsed < 2000, f"10 rapid ingest calls took {elapsed:.1f}ms (limit 2000ms)"
