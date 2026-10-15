import json
from unittest.mock import MagicMock, patch

import pytest

from app.api.v1 import evaluation as eval_module  # noqa: F401  (imported so the router is registered)
from app.core.config import settings
from app.graph.nodes.ambiguity_node import ambiguity_node
from app.models.trace import Trace
from app.services import answer_generator, llm
from app.services.chunking_service import chunk_text
from app.services.confidence_service import calculate_confidence_with_breakdown
from app.services.llm import FallbackLLM, LLMQuotaExhausted
from app.services.text_cleaning import PAGE_BREAK, clean_text

DAILY = "Error code: 429 - quota exceeded, limit: 500. Please retry in 6h30m2.3s."
MINUTE = "Error code: 429 - quota exceeded, limit: 5. Please retry in 32.4s."


@pytest.fixture(autouse=True)
def clean_state():
    llm.reset_exhausted()
    answer_generator.clear_answer_cache()
    yield
    llm.reset_exhausted()
    answer_generator.clear_answer_cache()


# ---- provider quota handling -------------------------------------------------------------

def test_retry_hints_in_hours_minutes_and_seconds_are_parsed():
    assert llm.parse_retry_seconds(DAILY) == pytest.approx(6 * 3600 + 30 * 60 + 2.3)
    assert llm.parse_retry_seconds(MINUTE) == pytest.approx(32.4)
    assert llm.parse_retry_seconds("retry in 2m") == 120
    assert llm.parse_retry_seconds("no hint here") is None


def test_daily_quota_is_told_apart_from_a_per_minute_limit():
    assert llm.daily_quota_seconds(Exception(DAILY)) > 3600
    assert llm.daily_quota_seconds(Exception(MINUTE)) is None
    assert llm.daily_quota_seconds(Exception("Error code: 500 - boom")) is None


def _fake(result=None, error=None):
    client = MagicMock()
    if error:
        client.invoke.side_effect = error
    else:
        client.invoke.return_value = result
    return client


def test_a_model_over_its_daily_quota_is_skipped_for_the_next_one(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(settings, "GEMINI_MODEL", "m1")
    monkeypatch.setattr(settings, "GEMINI_FALLBACK_MODELS", "m2")
    first, second = _fake(error=Exception(DAILY)), _fake(result="from m2")
    pool = FallbackLLM({"m1": first, "m2": second})

    assert pool.invoke("q") == "from m2"
    assert pool.invoke("q again") == "from m2"
    assert first.invoke.call_count == 1  # m1 is not asked again once it is known to be exhausted
    assert llm.llm_status()["exhausted"] is False


def test_when_every_model_is_exhausted_calls_fail_fast_and_status_says_so(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(settings, "GEMINI_MODEL", "m1")
    monkeypatch.setattr(settings, "GEMINI_FALLBACK_MODELS", "m2")
    pool = FallbackLLM({"m1": _fake(error=Exception(DAILY)), "m2": _fake(error=Exception(DAILY))})

    with pytest.raises(LLMQuotaExhausted) as exc:
        pool.invoke("q")
    assert "resets in about" in str(exc.value)
    status = llm.llm_status()
    assert status["exhausted"] is True and status["retry_after_seconds"] > 3600

    with patch("app.services.llm.time.sleep") as sleep:
        with pytest.raises(LLMQuotaExhausted):
            llm.invoke_with_retry(pool, "q")  # never waits out a daily quota
    sleep.assert_not_called()


def test_per_minute_limits_do_not_mark_a_model_exhausted(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(settings, "GEMINI_MODEL", "m1")
    monkeypatch.setattr(settings, "GEMINI_FALLBACK_MODELS", "")
    pool = FallbackLLM({"m1": _fake(error=Exception(MINUTE))})
    with pytest.raises(Exception, match="429"):
        pool.invoke("q")
    assert llm.llm_status()["exhausted"] is False


def test_fallback_models_come_after_the_primary_without_duplicates(monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(settings, "GEMINI_MODEL", "a")
    monkeypatch.setattr(settings, "GEMINI_FALLBACK_MODELS", "b, a ,c")
    assert settings.llm_model_candidates == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_ready_and_evaluate_report_an_exhausted_quota(async_client, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(settings, "GEMINI_MODEL", "m1")
    monkeypatch.setattr(settings, "GEMINI_FALLBACK_MODELS", "")
    llm.mark_exhausted("m1", 7200)

    ready = (await async_client.get("/api/v1/ready")).json()
    assert ready["llm"]["status"] == "quota_exhausted" and ready["llm"]["retry_after_seconds"] > 7000

    r = await async_client.post("/api/v1/evaluate")
    assert r.status_code == 409 and "quota" in r.json()["detail"]


# ---- answer cache --------------------------------------------------------------------------

CHUNKS = [{"chunk_id": "c1", "document_id": "d1", "text": "Refunds within 30 days."}]


def test_identical_question_and_passages_are_answered_from_the_cache():
    model = MagicMock()
    model.invoke.return_value = MagicMock(content="30 days [Source 1].")
    with patch.object(answer_generator, "_get_llm", return_value=model):
        first = answer_generator.generate_answer("What is the refund window?", CHUNKS)
        second = answer_generator.generate_answer("  what is the refund window? ", CHUNKS)
        answer_generator.generate_answer("What is the refund window?", [{**CHUNKS[0], "chunk_id": "c2"}])
    assert first == second == "30 days [Source 1]."
    assert model.invoke.call_count == 2  # the repeat was free; different passages were not


def test_fallback_answers_are_never_cached():
    model = MagicMock()
    model.invoke.side_effect = [Exception("Error code: 401 - bad key"), MagicMock(content="real answer")]
    with patch.object(answer_generator, "_get_llm", return_value=model):
        first = answer_generator.generate_answer("Q?", CHUNKS)
        second = answer_generator.generate_answer("Q?", CHUNKS)
    assert "LLM is unavailable" in first and second == "real answer"


def test_quota_exhaustion_produces_a_clear_notice_not_a_silent_fallback():
    model = MagicMock()
    model.invoke.side_effect = LLMQuotaExhausted(6 * 3600)
    with patch.object(answer_generator, "_get_llm", return_value=model):
        answer = answer_generator.generate_answer("Q?", CHUNKS)
    assert "quota is used up" in answer and "6 hour" in answer and "Refunds within 30 days" in answer


# ---- confidence for small documents ---------------------------------------------------------

def test_a_one_chunk_document_is_not_penalised_for_coverage():
    args = dict(vector_scores=[0.7], rerank_scores=[2.0], total_results=1)
    _, normal = calculate_confidence_with_breakdown(**args)
    result, small = calculate_confidence_with_breakdown(**args, coverage_full=True)
    assert normal["coverage"] == 0.2 and small["coverage"] == 1.0
    assert small["final_score"] > normal["final_score"]
    assert result.score == small["final_score"]


# ---- answer anyway ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_answer_anyway_skips_the_ambiguity_check_without_an_llm_call():
    model = MagicMock()
    with patch("app.services.clarification_service._get_llm", return_value=model):
        update = await ambiguity_node({"question": "Tell me about it", "skip_clarification": True,
                                       "reasoning_path": [], "graph_execution": [], "latencies": {}})
    model.invoke.assert_not_called()
    assert "clarification_needed" not in update
    assert update["graph_execution"][0]["output"].startswith("skipped (user chose")


# ---- page numbers ----------------------------------------------------------------------------

def test_chunks_record_the_page_they_start_on():
    page1 = "Alpha policy text. " * 130
    page2 = "Beta policy text. " * 130
    text = page1.strip() + "\n\n" + PAGE_BREAK + "\n\n" + page2.strip()
    chunks = chunk_text(text)
    assert chunks[0].page_number == 1
    assert any(c.page_number == 2 for c in chunks)
    assert all(c.page_number in (1, 2) for c in chunks)


def test_single_page_documents_get_page_one_when_paginated():
    assert chunk_text("Short single page text.", paginated=True)[0].page_number == 1
    assert chunk_text("Short single page text.")[0].page_number is None  # plain text has no pages


def test_cleaning_keeps_page_breaks():
    cleaned = clean_text("First page\n3\n" + PAGE_BREAK + "Second page text")
    assert cleaned.count(PAGE_BREAK) == 1
    assert cleaned.split(PAGE_BREAK)[1] == "Second page text"
    assert "3" not in cleaned.split(PAGE_BREAK)[0].split()  # per-page cleanup still removes the page number


# ---- dashboard numbers from real questions -----------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_reports_response_time_and_correction_rate(async_client, db_session, test_user):
    def trace(i, nodes, attempts):
        return Trace(id=f"t{i}", user_id=test_user.id, original_query="q", retrieval_attempts=attempts,
                     latencies=json.dumps({**nodes, "total": 99999}))

    db_session.add(trace(1, {"retrieve_node": 400.0, "generation_node": 600.0}, 1))
    db_session.add(trace(2, {"retrieve_node": 800.0, "retry_node": 500.0, "generation_node": 700.0}, 2))
    await db_session.commit()

    stats = (await async_client.get("/api/v1/dashboard/stats")).json()
    assert stats["avg_response_ms"] == 1500  # (1000 + 2000) / 2, node times only
    assert stats["self_correction_rate"] == 50.0
    assert stats["questions_answered"] == 2


@pytest.mark.asyncio
async def test_dashboard_numbers_are_empty_not_invented_without_questions(async_client):
    stats = (await async_client.get("/api/v1/dashboard/stats")).json()
    assert stats["avg_response_ms"] is None and stats["self_correction_rate"] is None
