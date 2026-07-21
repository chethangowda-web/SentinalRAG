import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.exceptions import AppException
from app.services.query_preprocessor import preprocess_query
from app.services.vector_search_service import VectorSearchResult, search_vector
from app.services.bm25_service import BM25Result, search_bm25
from app.services.hybrid_search_service import fuse_results, HybridResult
from app.services.confidence_service import calculate_confidence
from app.services.retrieval_service import retrieve, SearchResponse
from app.schemas.search import SearchRequest


class TestQueryPreprocessor:
    def test_normalizes_whitespace(self):
        assert preprocess_query("  hello   world  ") == "hello world"

    def test_lowercases(self):
        assert preprocess_query("Hello World") == "hello world"

    def test_removes_punctuation(self):
        result = preprocess_query("What's the price? (urgent)!")
        assert "?" not in result
        assert "!" not in result
        assert "(" not in result
        assert ")" not in result

    def test_keeps_technical_identifiers(self):
        result = preprocess_query("module-4_api v2.0 @user #bug123")
        assert "module-4" in result
        assert "v2.0" in result

    def test_empty_query_returns_empty(self):
        assert preprocess_query("") == ""
        assert preprocess_query("   ") == ""

    def test_preserves_reasonable_length(self):
        result = preprocess_query("  Find  the  refund  policy  for  returns.  ")
        assert result == "find the refund policy for returns."


class TestVectorSearch:
    def test_search_returns_results(self):
        with patch("app.services.vector_search_service.generate_embeddings") as mock_embed:
            mock_embed.return_value = [[0.1] * 384]
            with patch("app.services.vector_search_service.get_qdrant_client") as mock_qdrant:
                mock_client = MagicMock()
                mock_result = MagicMock()
                mock_result.score = 0.92
                mock_result.payload = {
                    "chunk_id": "chunk-1",
                    "document_id": "doc-1",
                    "text": "Refund policy text",
                    "page_number": 3,
                    "section": "Refund Policy",
                    "filename": "contract.pdf",
                    "chunk_index": 0,
                }
                mock_client.search.return_value = [mock_result]
                mock_qdrant.return_value = mock_client

                results = search_vector("refund policy", top_k=20)
                assert len(results) == 1
                assert results[0].chunk_id == "chunk-1"
                assert results[0].score == 0.92
                assert results[0].page_number == 3

    def test_search_empty_embedding(self):
        with patch("app.services.vector_search_service.generate_embeddings") as mock_embed:
            mock_embed.return_value = []
            results = search_vector("test")
            assert results == []

    def test_search_qdrant_error(self):
        with patch("app.services.vector_search_service.generate_embeddings") as mock_embed:
            mock_embed.return_value = [[0.1] * 384]
            with patch("app.services.vector_search_service.get_qdrant_client") as mock_qdrant:
                from qdrant_client.http.exceptions import UnexpectedResponse
                mock_client = MagicMock()
                mock_client.search.side_effect = UnexpectedResponse(503, "Service Unavailable", b"", {})
                mock_qdrant.return_value = mock_client
                results = search_vector("test")
                assert results == []

    def test_search_returns_multiple(self):
        with patch("app.services.vector_search_service.generate_embeddings") as mock_embed:
            mock_embed.return_value = [[0.1] * 384]
            with patch("app.services.vector_search_service.get_qdrant_client") as mock_qdrant:
                mock_client = MagicMock()
                mock_client.search.return_value = [
                    MagicMock(score=0.9, payload={"chunk_id": f"c{i}", "document_id": "d1", "text": f"text {i}"})
                    for i in range(3)
                ]
                mock_qdrant.return_value = mock_client
                results = search_vector("test")
                assert len(results) == 3


class TestBM25Search:
    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        mock_db = AsyncMock(spec=True)
        mock_result = MagicMock()
        mock_result.chunk_id = "chunk-1"
        mock_result.document_id = "doc-1"
        mock_result.chunk_text = "Refund policy text"
        mock_result.page_number = 3
        mock_result.word_count = 50
        mock_result.filename = "contract.pdf"

        mock_execute = MagicMock()
        mock_execute.fetchall.return_value = [mock_result]

        async def fake_execute(*a, **kw):
            return mock_execute
        mock_db.execute = fake_execute

        results = await search_bm25("refund policy", mock_db)
        assert len(results) == 1
        assert results[0].chunk_id == "chunk-1"
        assert results[0].score > 0

    @pytest.mark.asyncio
    async def test_search_empty_query(self):
        results = await search_bm25("", AsyncMock())
        assert results == []

    @pytest.mark.asyncio
    async def test_search_db_error(self):
        mock_db = AsyncMock()
        mock_db.execute.side_effect = Exception("DB error")
        results = await search_bm25("test", mock_db)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_normalizes_scores(self):
        mock_db = AsyncMock(spec=True)
        mock_execute = MagicMock()
        mock_execute.fetchall.return_value = [
            MagicMock(chunk_id="c1", document_id="d1", chunk_text="a", page_number=None, word_count=100, filename="f1", bm25_score=10.0),
            MagicMock(chunk_id="c2", document_id="d2", chunk_text="b", page_number=None, word_count=50, filename="f2", bm25_score=5.0),
        ]

        async def fake_execute(*a, **kw):
            return mock_execute
        mock_db.execute = fake_execute

        results = await search_bm25("test", mock_db)
        assert len(results) == 2
        assert results[0].score == 1.0
        assert results[1].score == 0.5


class TestHybridFusion:
    def test_fuses_vector_and_bm25(self):
        vector = [
            VectorSearchResult(chunk_id="c1", document_id="d1", text="t1", score=0.9),
            VectorSearchResult(chunk_id="c2", document_id="d1", text="t2", score=0.8),
        ]
        bm25 = [
            BM25Result(chunk_id="c1", document_id="d1", text="t1", score=1.0),
            BM25Result(chunk_id="c3", document_id="d2", text="t3", score=0.7),
        ]
        fused = fuse_results(vector, bm25, top_k=10)
        assert len(fused) == 3
        c1 = [f for f in fused if f.chunk_id == "c1"][0]
        assert c1.vector_score == 0.9
        assert c1.bm25_score == 1.0
        assert c1.rrf_score > 0

    def test_rrf_orders_by_score(self):
        vector = [
            VectorSearchResult(chunk_id="c1", document_id="d1", text="t1", score=0.9),
            VectorSearchResult(chunk_id="c2", document_id="d1", text="t2", score=0.8),
        ]
        bm25 = [
            BM25Result(chunk_id="c2", document_id="d1", text="t2", score=1.0),
        ]
        fused = fuse_results(vector, bm25, top_k=10)
        assert fused[0].chunk_id == "c2"
        assert fused[0].rrf_score > fused[1].rrf_score

    def test_deduplicates_by_chunk_id(self):
        vector = [
            VectorSearchResult(chunk_id="c1", document_id="d1", text="t1", score=0.9),
        ]
        bm25 = [
            BM25Result(chunk_id="c1", document_id="d1", text="t1", score=0.8),
        ]
        fused = fuse_results(vector, bm25, top_k=10)
        assert len(fused) == 1

    def test_empty_inputs(self):
        assert fuse_results([], [], top_k=10) == []

    def test_respects_top_k(self):
        vector = [VectorSearchResult(chunk_id=f"c{i}", document_id="d1", text=f"t{i}", score=0.5) for i in range(10)]
        bm25 = [BM25Result(chunk_id=f"c{i}", document_id="d1", text=f"t{i}", score=0.5) for i in range(5)]
        fused = fuse_results(vector, bm25, top_k=3)
        assert len(fused) == 3


class TestConfidenceService:
    def test_high_confidence(self):
        result = calculate_confidence(
            vector_scores=[0.95, 0.90, 0.85],
            rerank_scores=[0.92, 0.88, 0.82],
            total_results=10,
        )
        assert result.score >= 80.0
        assert result.level == "HIGH"

    def test_medium_confidence(self):
        result = calculate_confidence(
            vector_scores=[0.6, 0.55],
            rerank_scores=[0.5, 0.45],
            total_results=5,
        )
        assert 50.0 <= result.score < 80.0
        assert result.level == "MEDIUM"

    def test_low_confidence(self):
        result = calculate_confidence(
            vector_scores=[0.2, 0.15],
            rerank_scores=[0.1, 0.05],
            total_results=2,
        )
        assert result.score < 50.0
        assert result.level == "LOW"

    def test_no_results(self):
        result = calculate_confidence(
            vector_scores=[],
            rerank_scores=[],
            total_results=0,
        )
        assert result.score == 0.0
        assert result.level == "LOW"

    def test_coverage_boosts_confidence(self):
        many = calculate_confidence(
            vector_scores=[0.7, 0.7],
            rerank_scores=[0.6, 0.6],
            total_results=10,
        )
        few = calculate_confidence(
            vector_scores=[0.7, 0.7],
            rerank_scores=[0.6, 0.6],
            total_results=1,
        )
        assert many.score > few.score

    def test_score_clamped(self):
        result = calculate_confidence(
            vector_scores=[1.0, 1.0],
            rerank_scores=[1.0, 1.0],
            total_results=10,
        )
        assert result.score <= 100.0


class TestRetrievalService:
    @pytest.mark.asyncio
    async def test_empty_query_raises(self):
        with pytest.raises(AppException) as exc:
            await retrieve("", AsyncMock())
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_whitespace_query_raises(self):
        with pytest.raises(AppException):
            await retrieve("   ", AsyncMock())

    @pytest.mark.asyncio
    async def test_retrieve_full_pipeline(self, db_session):
        with patch("app.services.vector_search_service.search_vector") as mock_vec:
            mock_vec.return_value = [
                VectorSearchResult(
                    chunk_id="c1", document_id="d1", text="refund policy text",
                    score=0.92, page_number=3, section="Refund Policy", filename="doc.pdf",
                ),
            ]
            with patch("app.services.bm25_service.search_bm25", new_callable=AsyncMock) as mock_bm25:
                mock_bm25.return_value = [
                    BM25Result(
                        chunk_id="c1", document_id="d1", text="refund policy text",
                        score=1.0, page_number=3, filename="doc.pdf",
                    ),
                ]
                with patch("app.services.reranker_service._load_reranker") as mock_rerank:
                    mock_model = MagicMock()
                    mock_model.predict.return_value = [0.97]
                    mock_rerank.return_value = mock_model

                    result = await retrieve("refund policy", db_session)
                    assert isinstance(result, SearchResponse)
                    assert len(result.results) > 0
                    assert result.confidence > 0
                    assert result.confidence_level in ("HIGH", "MEDIUM", "LOW")
                    assert result.latencies is not None
                    assert "total" in result.latencies

    @pytest.mark.asyncio
    async def test_no_results(self, db_session):
        with patch("app.services.vector_search_service.search_vector") as mock_vec:
            mock_vec.return_value = []
            with patch("app.services.bm25_service.search_bm25", new_callable=AsyncMock) as mock_bm25:
                mock_bm25.return_value = []
                result = await retrieve("nonexistent term xyz", db_session)
                assert len(result.results) == 0
                assert result.confidence == 0.0
                assert result.confidence_level == "LOW"

    @pytest.mark.asyncio
    async def test_latencies_recorded(self, db_session):
        with patch("app.services.vector_search_service.search_vector") as mock_vec:
            mock_vec.return_value = [
                VectorSearchResult(chunk_id="c1", document_id="d1", text="t1", score=0.9),
            ]
            with patch("app.services.bm25_service.search_bm25", new_callable=AsyncMock) as mock_bm25:
                mock_bm25.return_value = [
                    BM25Result(chunk_id="c1", document_id="d1", text="t1", score=1.0),
                ]
                with patch("app.services.reranker_service._load_reranker") as mock_rerank:
                    mock_model = MagicMock()
                    mock_model.predict.return_value = [0.95]
                    mock_rerank.return_value = mock_model

                    result = await retrieve("test query", db_session)
                    required_keys = {"vector_search", "bm25_search", "fusion", "rerank", "confidence", "total"}
                    assert required_keys.issubset(result.latencies.keys())
                    for v in result.latencies.values():
                        assert v >= 0


class TestSearchAPI:
    @pytest.mark.asyncio
    async def test_search_endpoint_success(self, async_client, db_session):
        with patch("app.services.retrieval_service.retrieve", new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.return_value = SearchResponse(
                query="refund policy",
                confidence=91.5,
                confidence_level="HIGH",
                results=[
                    MagicMock(
                        chunk_id="c1", document_id="d1", text="refund policy text",
                        page_number=3, section="Refund Policy", filename="doc.pdf",
                        vector_score=0.92, bm25_score=1.0, rerank_score=0.97,
                    ),
                ],
                latencies={"total": 150.0, "vector_search": 50.0, "bm25_search": 40.0,
                           "fusion": 5.0, "rerank": 30.0, "confidence": 2.0},
            )

            response = await async_client.post(
                "/api/v1/search",
                json={"query": "refund policy"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == "refund policy"
            assert data["confidence"] == 91.5
            assert data["confidence_level"] == "HIGH"
            assert len(data["results"]) == 1
            assert data["results"][0]["chunk_id"] == "c1"
            assert data["results"][0]["page"] == 3
            assert data["results"][0]["rerank_score"] == 0.97

    @pytest.mark.asyncio
    async def test_search_endpoint_empty_query(self, async_client, db_session):
        response = await async_client.post(
            "/api/v1/search",
            json={"query": ""},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_search_endpoint_no_results(self, async_client, db_session):
        with patch("app.services.retrieval_service.retrieve", new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.return_value = SearchResponse(
                query="xyz nonexistent",
                confidence=0.0,
                confidence_level="LOW",
                results=[],
                latencies={"total": 100.0},
            )
            response = await async_client.post(
                "/api/v1/search",
                json={"query": "xyz nonexistent"},
            )
            assert response.status_code == 200
            assert len(response.json()["results"]) == 0
            assert response.json()["confidence"] == 0.0

    @pytest.mark.asyncio
    async def test_search_endpoint_whitespace_only(self, async_client, db_session):
        response = await async_client.post(
            "/api/v1/search",
            json={"query": "   "},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_search_endpoint_missing_field(self, async_client, db_session):
        response = await async_client.post(
            "/api/v1/search",
            json={},
        )
        assert response.status_code == 422
