from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from qdrant_client.http.models import MatchAny, MatchValue

from app.core.config import settings
from app.schemas.chat import ChatRequest
from app.services import llm, retrieval_service, vector_search_service
from app.services.llm import FallbackLLM


# ---- several documents at once -----------------------------------------------------------------------

def _filter_used(**kwargs):
    with patch("app.services.vector_search_service.embed_query", return_value=[0.1] * 4), \
            patch("app.services.vector_search_service.get_qdrant_client") as get_client:
        client = MagicMock()
        client.query_points.return_value.points = []
        get_client.return_value = client
        vector_search_service.search_vector("refund", user_id="u1", **kwargs)
        return client.query_points.call_args.kwargs["query_filter"]


def test_one_document_still_matches_by_value():
    conditions = {c.key: c.match for c in _filter_used(document_id="d1").must}
    assert conditions["user_id"] == MatchValue(value="u1") and conditions["document_id"] == MatchValue(value="d1")


def test_several_documents_match_any_of_them_and_always_the_owner():
    conditions = {c.key: c.match for c in _filter_used(document_ids=["d1", "d2"]).must}
    assert conditions["document_id"] == MatchAny(any=["d1", "d2"])
    assert conditions["user_id"] == MatchValue(value="u1")  # another user's document id never widens the search


def test_no_scope_searches_everything_the_user_owns():
    keys = [c.key for c in _filter_used().must]
    assert keys == ["user_id"]


@pytest.mark.asyncio
async def test_retrieval_hands_the_chosen_documents_to_both_searches(monkeypatch):
    monkeypatch.setattr(retrieval_service, "_gate", None)
    vector = AsyncMock(return_value=[])
    bm25 = AsyncMock(return_value=[])
    monkeypatch.setattr(retrieval_service.vector_search_service, "search_vector_async", vector)
    monkeypatch.setattr(retrieval_service.bm25_service, "search_bm25", bm25)
    await retrieval_service.retrieve("refund window", None, user_id="u1", document_ids=["d1", "d2"])
    assert vector.call_args.kwargs["document_ids"] == ["d1", "d2"]
    assert bm25.call_args.kwargs["document_ids"] == ["d1", "d2"]


def test_a_chat_request_may_name_a_limited_number_of_documents():
    assert ChatRequest(question="q", document_ids=["a", "b"]).document_ids == ["a", "b"]
    with pytest.raises(ValueError):
        ChatRequest(question="q", document_ids=[str(i) for i in range(26)])


@pytest.mark.asyncio
async def test_the_bm25_filter_lists_every_chosen_document():
    from app.services import bm25_service

    captured = {}

    class FakeResult:
        def fetchall(self):
            return []

    class FakeSession:
        async def execute(self, statement, params=None):
            captured["sql"] = str(statement)
            captured["params"] = params
            return FakeResult()

    await bm25_service.search_bm25("refund policy", FakeSession(), user_id="u1", document_ids=["d1", "d2", "d3"])
    assert "c.document_id IN (:doc0, :doc1, :doc2)" in captured["sql"]
    assert [captured["params"][f"doc{i}"] for i in range(3)] == ["d1", "d2", "d3"]
    assert captured["params"]["user_id"] == "u1"


# ---- a second LLM provider ----------------------------------------------------------------------------

def _gemini(monkeypatch, second=True):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(settings, "GEMINI_MODEL", "m1")
    monkeypatch.setattr(settings, "GEMINI_FALLBACK_MODELS", "m2")
    monkeypatch.setattr(settings, "FALLBACK_LLM_API_KEY", "gk" if second else "")
    monkeypatch.setattr(settings, "FALLBACK_LLM_MODEL", "llama-3.3-70b-versatile" if second else "")


def test_the_second_provider_comes_last_and_only_when_fully_configured(monkeypatch):
    _gemini(monkeypatch)
    assert settings.llm_model_candidates == ["m1", "m2", "fallback:llama-3.3-70b-versatile"]
    _gemini(monkeypatch, second=False)
    assert settings.llm_model_candidates == ["m1", "m2"]


def test_when_every_gemini_model_is_busy_the_second_provider_answers(monkeypatch):
    _gemini(monkeypatch)
    llm.reset_exhausted()
    busy = Exception("Error code: 503 - This model is currently experiencing high demand.")
    first, second, groq = MagicMock(), MagicMock(), MagicMock()
    first.invoke.side_effect = busy
    second.invoke.side_effect = busy
    groq.invoke.return_value = "from the second provider"
    pool = FallbackLLM({"m1": first, "m2": second, "fallback:llama-3.3-70b-versatile": groq})
    with patch("app.services.llm.time.sleep") as sleep:
        assert llm.invoke_with_retry(pool, "q") == "from the second provider"
    sleep.assert_not_called()
    llm.reset_exhausted()


def test_the_second_provider_gets_its_own_credentials_and_no_gemini_reasoning(monkeypatch):
    _gemini(monkeypatch)
    monkeypatch.setattr(settings, "GEMINI_MODEL_REASONING", "m1=none")
    built = {}

    class FakeChat:
        def __init__(self, **kwargs):
            built[kwargs["model"]] = kwargs

    with patch("langchain_openai.ChatOpenAI", FakeChat):
        llm.build_llm(max_tokens=10, timeout=5)

    groq = built["llama-3.3-70b-versatile"]
    assert groq["api_key"] == "gk" and groq["base_url"] == settings.FALLBACK_LLM_BASE_URL
    assert "reasoning_effort" not in groq
    assert built["m1"]["api_key"] == "k" and built["m1"]["reasoning_effort"] == "none"
