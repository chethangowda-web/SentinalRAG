import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.graph.nodes.ambiguity_node import ambiguity_node, needs_check
from app.graph.nodes.confidence_node import route_after_confidence
from app.graph.nodes.retrieve_node import retrieve_node
from app.services import llm
from app.services.llm import FallbackLLM

BUSY = Exception("Error code: 503 - This model is currently experiencing high demand.")


@pytest.fixture(autouse=True)
def _clean():
    llm.reset_exhausted()
    yield
    llm.reset_exhausted()


def _gemini(monkeypatch, primary="m1", fallbacks="m2"):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(settings, "GEMINI_MODEL", primary)
    monkeypatch.setattr(settings, "GEMINI_FALLBACK_MODELS", fallbacks)


# ---- fail over instead of waiting ---------------------------------------------------------------

def test_an_overloaded_model_is_skipped_for_the_next_one_without_waiting(monkeypatch):
    _gemini(monkeypatch)
    first, second = MagicMock(), MagicMock()
    first.invoke.side_effect = BUSY
    second.invoke.return_value = "from m2"
    with patch("app.services.llm.time.sleep") as sleep:
        assert llm.invoke_with_retry(FallbackLLM({"m1": first, "m2": second}), "q") == "from m2"
    sleep.assert_not_called()
    assert llm.llm_status()["exhausted"] is False  # a busy model is not an exhausted one


def test_when_every_model_is_busy_the_error_reaches_the_retry_loop(monkeypatch):
    _gemini(monkeypatch)
    pool = FallbackLLM({"m1": MagicMock(invoke=MagicMock(side_effect=BUSY)), "m2": MagicMock(invoke=MagicMock(side_effect=BUSY))})
    with pytest.raises(Exception, match="503"):
        pool.invoke("q")


def test_a_real_error_is_not_swallowed_by_failover(monkeypatch):
    _gemini(monkeypatch)
    second = MagicMock()
    pool = FallbackLLM({"m1": MagicMock(invoke=MagicMock(side_effect=Exception("Error code: 400 - bad"))), "m2": second})
    with pytest.raises(Exception, match="400"):
        pool.invoke("q")
    second.invoke.assert_not_called()


def test_reasoning_is_switched_off_only_for_the_models_that_accept_it(monkeypatch):
    _gemini(monkeypatch, primary="gemini-3.5-flash", fallbacks="gemini-3.5-flash-lite")
    monkeypatch.setattr(settings, "GEMINI_MODEL_REASONING", "gemini-3.5-flash=none")
    monkeypatch.setattr(settings, "LLM_REASONING_EFFORT", "")
    assert settings.reasoning_effort_for("gemini-3.5-flash") == "none"
    assert settings.reasoning_effort_for("gemini-3.5-flash-lite") == ""


# ---- no needless rewrite --------------------------------------------------------------------------

def _state(level, best):
    return {"confidence_level": level, "retrieved_chunks": [{"rerank_score": best}]}


def test_a_relevant_medium_result_is_answered_without_rewriting():
    assert route_after_confidence(_state("MEDIUM", -0.18)) == "generate_answer"


def test_weak_or_low_results_are_still_rewritten():
    assert route_after_confidence(_state("MEDIUM", -6.0)) == "rewrite_query"
    assert route_after_confidence(_state("LOW", 2.0)) == "rewrite_query"


# ---- ambiguity check runs alongside retrieval -------------------------------------------------------

def test_only_short_unforced_questions_are_checked():
    assert needs_check({"question": "Tell me about the policy"})
    assert not needs_check({"question": "How many days do customers have to request a refund?"})
    assert not needs_check({"question": "Tell me about it", "skip_clarification": True})
    assert not needs_check({"question": "Tell me about it", "context_resolved": True})


@pytest.mark.asyncio
async def test_the_ambiguity_check_overlaps_retrieval_and_its_verdict_is_reused():
    def slow_check(question, chunks, use_keywords, titles):
        time.sleep(0.3)
        return "Which policy?"

    async def slow_retrieve(*args, **kwargs):
        await asyncio.sleep(0.3)
        response = MagicMock(results=[], confidence=50.0, confidence_level="MEDIUM", corpus_small=False, latencies={})
        return response

    state = {"question": "Tell me about the policy", "reasoning_path": [], "graph_execution": [], "latencies": {}, "retry_count": 0}
    with patch("app.graph.nodes.retrieve_node.detect_ambiguity", side_effect=slow_check), \
            patch("app.graph.nodes.retrieve_node.retrieve", new=slow_retrieve):
        t0 = time.perf_counter()
        update = await retrieve_node(state, {"configurable": {"db": None, "user_id": "u"}})
        elapsed = time.perf_counter() - t0
    assert elapsed < 0.55  # ~0.3 s overlapped, not 0.6 s one after the other
    assert update["ambiguity_precheck"] == {"clarification": "Which policy?"}

    with patch("app.graph.nodes.ambiguity_node.detect_ambiguity") as again:
        result = await ambiguity_node({**state, **update})
    again.assert_not_called()  # the verdict computed during retrieval is used, not asked again
    assert result["clarification_needed"] is True and result["clarification_question"] == "Which policy?"
