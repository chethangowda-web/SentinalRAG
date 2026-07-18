import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.asyncio


@pytest.fixture
def sample_text():
    return " ".join(["The quick brown fox jumps over the lazy dog." for _ in range(200)])


@pytest.fixture
def sample_chunks():
    return [
        {"text": "Revenue in Q4 2024 was $12.4 billion representing 15% growth year over year.", "chunk_index": 0,
         "page_number": 5},
        {"text": "The company reported total assets of $89.3 billion as of December 31 2024.", "chunk_index": 1,
         "page_number": 6},
        {"text": "Operating expenses increased by 8% to $6.2 billion driven by R&D investments.", "chunk_index": 2,
         "page_number": 7},
        {"text": "Cash flow from operations was $18.7 billion for the full fiscal year.", "chunk_index": 3,
         "page_number": 8},
        {"text": "The board approved a $15 billion share buyback program to be executed over 12 months.", "chunk_index": 4,
         "page_number": 9},
    ]


class TestTextCleaningPerformance:
    def test_text_cleaning_latency(self, benchmark, sample_text):
        from app.services.text_cleaning import clean_text

        result = benchmark(clean_text, sample_text)
        assert len(result) > 0

    def test_text_cleaning_large_text(self, benchmark):
        from app.services.text_cleaning import clean_text

        large = "Page 1\nHeader\n" + " ".join(["test paragraph." for _ in range(5000)]) + "\nFooter\nPage 2\n"
        result = benchmark(clean_text, large)
        assert len(result) > 0


class TestChunkingPerformance:
    def test_chunking_latency(self, benchmark, sample_text):
        from app.services.chunking_service import chunk_text

        cleaned = sample_text.lower()
        chunks = benchmark(chunk_text, cleaned)
        assert len(chunks) > 0

    def test_chunking_large_document(self, benchmark):
        from app.services.chunking_service import chunk_text

        text = "\n\n".join([f"Paragraph {i}. " + "words " * 250 for i in range(50)])
        chunks = benchmark(chunk_text, text)
        assert len(chunks) > 0

    def test_chunking_longest_document(self):
        from app.services.chunking_service import chunk_text
        import time

        text = "\n\n".join([f"Section {i}. " + "content " * 500 for i in range(100)])
        start = time.perf_counter()
        chunks = chunk_text(text)
        elapsed = (time.perf_counter() - start) * 1000

        assert len(chunks) > 0
        assert elapsed < 5000, f"Chunking 100 sections took {elapsed:.1f}ms (limit 5000ms)"


class TestEmbeddingPerformance:
    def test_normalize_embedding_latency(self, benchmark):
        from app.services.embedding_service import normalize_embedding

        vec = [0.1 * i for i in range(384)]
        result = benchmark(normalize_embedding, vec)
        assert len(result) == 384

    def test_normalize_embedding_batch(self, benchmark):
        from app.services.embedding_service import normalize_embedding

        vectors = [[0.1 * (i + j) for i in range(384)] for j in range(32)]
        result = benchmark([normalize_embedding(v) for v in vectors])
        assert len(result) == 32
        assert all(len(r) == 384 for r in result)


class TestQueryPreprocessorPerformance:
    def test_preprocess_latency(self, benchmark):
        from app.services.query_preprocessor import preprocess_query

        query = "What was Apple's total revenue in Q4 2024, and how does it compare to the previous quarter?"
        result = benchmark(preprocess_query, query)
        assert len(result) > 0

    def test_preprocess_long_query(self, benchmark):
        from app.services.query_preprocessor import preprocess_query

        query = " ".join(["detailed analysis of financial performance" for _ in range(100)])
        result = benchmark(preprocess_query, query)
        assert len(result) > 0


class TestConfidenceServicePerformance:
    def test_confidence_calculation(self, benchmark, sample_chunks):
        from app.services.confidence_service import calculate_confidence

        chunk_scores = [
            {"vector_score": c.get("vector_score", 0.85), "rerank_score": c.get("rerank_score", 0.90)}
            for c in sample_chunks
        ]
        result = benchmark(calculate_confidence, chunk_scores)
        assert isinstance(result, dict)


class TestVectorSearchPerformance:
    @patch("app.services.vector_search_service.get_qdrant_client")
    async def test_search_vector_latency(self, mock_get_client, benchmark):
        from app.services.vector_search_service import search_vector

        mock_client = MagicMock()
        mock_client.search.return_value = [
            MagicMock(id=f"chunk_{i}", score=0.95 - i * 0.05, payload={
                "chunk_text": f"text {i}", "document_id": "doc1", "chunk_index": i, "page_number": i
            })
            for i in range(10)
        ]
        mock_get_client.return_value = mock_client

        result = await benchmark(search_vector, "test query", top_k=10)
        assert len(result) == 10


class TestBM25SearchPerformance:
    @patch("app.services.bm25_service.get_db")
    async def test_search_bm25_latency(self, mock_get_db, benchmark):
        from app.services.bm25_service import search_bm25

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (f"chunk_{i}", f"doc_{i}", f"text {i}", 0.95 - i * 0.05, i, i)
            for i in range(10)
        ]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value.__aenter__.return_value = mock_session

        result = await benchmark(search_bm25, "test revenue query", top_k=10)
        assert len(result) == 10


class TestHybridSearchPerformance:
    def test_rrf_fusion(self, benchmark):
        from app.services.hybrid_search_service import fuse_results

        vector_results = [
            {"chunk_id": f"chunk_{i}", "document_id": "doc1", "text": f"text {i}", "score": 0.95 - i * 0.02,
             "page_number": i, "section": "test"}
            for i in range(10)
        ]
        bm25_results = [
            {"chunk_id": f"chunk_{i}", "document_id": "doc1", "text": f"text {i}", "score": 0.90 - i * 0.03,
             "page_number": i, "section": "test"}
            for i in range(10)
        ]
        result = benchmark(fuse_results, vector_results, bm25_results, top_k=10)
        assert len(result) > 0

    def test_rrf_fusion_large_sets(self, benchmark):
        from app.services.hybrid_search_service import fuse_results

        vector_results = [
            {"chunk_id": f"v_{i}", "document_id": "doc1", "text": f"text {i}", "score": 0.99 - i * 0.001,
             "page_number": i, "section": "test"}
            for i in range(100)
        ]
        bm25_results = [
            {"chunk_id": f"b_{i}", "document_id": "doc1", "text": f"text {i}", "score": 0.98 - i * 0.001,
             "page_number": i, "section": "test"}
            for i in range(100)
        ]
        result = benchmark(fuse_results, vector_results, bm25_results, top_k=20)
        assert len(result) <= 20


class TestRerankerPerformance:
    @patch("app.services.reranker_service._model")
    def test_rerank_latency(self, mock_model, benchmark):
        from app.services.reranker_service import rerank

        mock_model.predict.return_value.tolisten.return_value = [0.95, 0.85, 0.75]
        mock_model.predict.return_value = [0.95, 0.85, 0.75]

        query = "What is the revenue?"
        documents = [f"Document {i} content about financial results." for i in range(10)]
        result = benchmark(rerank, query, documents)
        assert len(result) > 0


class TestRetrievalPipelinePerformance:
    @patch("app.services.retrieval_service.search_vector")
    @patch("app.services.retrieval_service.search_bm25")
    async def test_full_retrieval_pipeline(self, mock_bm25, mock_vector, benchmark):
        from app.services.retrieval_service import retrieve

        mock_vector.return_value = [
            {"chunk_id": f"chunk_{i}", "document_id": "doc1", "text": f"text {i}", "score": 0.9 - i * 0.02,
             "page_number": i, "section": "test", "vector_score": 0.9 - i * 0.02, "rerank_score": 0.92 - i * 0.02,
             "bm25_score": 0.0}
            for i in range(10)
        ]
        mock_bm25.return_value = [
            {"chunk_id": f"chunk_{i}", "document_id": "doc1", "text": f"text {i}", "score": 0.85 - i * 0.03,
             "page_number": i, "section": "test", "vector_score": 0.0, "rerank_score": 0.0,
             "bm25_score": 0.85 - i * 0.03}
            for i in range(10)
        ]

        result = await benchmark(retrieve, "What is the revenue for Q4 2024?")
        assert "results" in result
        assert "latencies" in result


class TestConfidenceMetrics:
    def test_confidence_score_levels(self):
        from app.services.confidence_service import calculate_confidence

        high = calculate_confidence([{"vector_score": 0.92, "rerank_score": 0.95}])
        assert high["level"] == "HIGH"
        assert high["score"] >= 80

        medium = calculate_confidence([{"vector_score": 0.65, "rerank_score": 0.70}])
        assert medium["level"] == "MEDIUM"
        assert 50 <= medium["score"] < 80

        low = calculate_confidence([{"vector_score": 0.30, "rerank_score": 0.35}])
        assert low["level"] == "LOW"
        assert low["score"] < 50


class TestPerformanceBenchmark:
    @pytest.mark.timeout(30)
    def test_text_cleaning_benchmark(self):
        from app.services.text_cleaning import clean_text
        import time

        texts = [
            "Page 1\n" + "normal text. " * size + "\nFooter\nPage 2"
            for size in [100, 1000, 5000, 10000]
        ]
        for i, text in enumerate(texts):
            start = time.perf_counter()
            clean_text(text)
            elapsed = (time.perf_counter() - start) * 1000
            assert elapsed < 2000, f"Text cleaning size={len(text)} took {elapsed:.1f}ms"

    @pytest.mark.timeout(30)
    def test_chunking_scale(self):
        from app.services.chunking_service import chunk_text
        import time

        sizes = [1000, 5000, 10000, 50000]
        for size in sizes:
            text = " ".join(["word" for _ in range(size)])
            start = time.perf_counter()
            chunks = chunk_text(text)
            elapsed = (time.perf_counter() - start) * 1000
            assert elapsed < 5000, f"Chunking {size} words took {elapsed:.1f}ms"
            assert len(chunks) > 0
