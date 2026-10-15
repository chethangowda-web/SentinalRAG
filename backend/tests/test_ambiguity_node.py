from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.graph.nodes.ambiguity_node import MAX_WORDS_TO_CHECK, ambiguity_node, route_after_ambiguity
from app.services import clarification_service as cs


def _state(question: str) -> dict:
    return {"question": question, "retrieved_chunks": [], "reasoning_path": [], "graph_execution": [], "latencies": {}}


def _llm_replying(text: str):
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=text)
    return llm


@pytest.mark.asyncio
async def test_short_vague_question_gets_a_clarifying_question():
    with patch.object(cs, "_get_llm", return_value=_llm_replying("Which part of the network do you mean?")):
        update = await ambiguity_node(_state("Tell me about the network"))
    assert update["clarification_needed"] is True
    assert update["clarification_question"] == "Which part of the network do you mean?"
    assert update["reasoning_path"] == ["ambiguity_check"]
    assert route_after_ambiguity({"clarification_needed": True}) == "end"


@pytest.mark.asyncio
async def test_short_specific_question_is_cleared():
    with patch.object(cs, "_get_llm", return_value=_llm_replying("CLEAR")):
        update = await ambiguity_node(_state("When is maintenance scheduled?"))
    assert "clarification_needed" not in update
    assert update["graph_execution"][0]["output"] == "clear"
    assert route_after_ambiguity(update) == "confidence_evaluate"


@pytest.mark.asyncio
async def test_clear_reply_with_trailing_text_still_counts_as_clear():
    with patch.object(cs, "_get_llm", return_value=_llm_replying("CLEAR.")):
        assert cs.detect_ambiguity("What is the refund window?", [], use_keywords=False) is None


@pytest.mark.asyncio
async def test_long_questions_skip_the_check_and_cost_no_llm_call():
    question = " ".join(["word"] * (MAX_WORDS_TO_CHECK + 1))
    llm = _llm_replying("this should never be asked")
    with patch.object(cs, "_get_llm", return_value=llm):
        update = await ambiguity_node(_state(question))
    llm.invoke.assert_not_called()
    assert "clarification_needed" not in update
    assert update["graph_execution"][0]["output"].startswith("skipped")


@pytest.mark.asyncio
async def test_node_does_not_use_the_keyword_screen():
    # "explain" is in the keyword list; a specific short question using it must not be flagged without the LLM.
    with patch.object(cs, "_get_llm", return_value=None):
        update = await ambiguity_node(_state("Explain refund steps"))
    assert "clarification_needed" not in update


def test_keyword_screen_is_still_available_to_other_callers():
    assert cs.detect_ambiguity("Tell me about something", [], use_keywords=True) is not None


@pytest.mark.asyncio
async def test_vague_question_ends_the_graph_with_a_question_and_no_retrieval_scoring(db_session):
    from app.graph.graph_builder import build_graph

    response = MagicMock()
    response.confidence = 70.0
    response.confidence_level = "HIGH"
    response.latencies = {"total": 5.0}
    response.results = []
    state = {
        "question": "Tell me about the network", "rewritten_question": None, "document_id": None,
        "retrieved_chunks": [], "confidence_score": 0.0, "confidence_level": "LOW", "confidence_reason": None,
        "retry_count": 0, "max_retries": 2, "contradiction_detected": False, "contradiction_reason": None,
        "clarification_needed": False, "clarification_question": None, "answer": None, "citations": [],
        "reasoning_path": [], "latencies": {}, "trace_id": "t", "graph_execution": [], "retrieval_details": [],
        "confidence_breakdown": None, "llm_observability": None,
    }
    with patch("app.graph.nodes.retrieve_node.retrieve", new_callable=AsyncMock, return_value=response), \
            patch.object(cs, "_get_llm", return_value=_llm_replying("Which aspect of the network?")):
        result = await build_graph().ainvoke(state, {"configurable": {"db": db_session}})

    assert result["clarification_needed"] is True
    assert result["clarification_question"] == "Which aspect of the network?"
    assert result["reasoning_path"] == ["retrieve", "ambiguity_check"]
    assert not result.get("answer")


@pytest.mark.asyncio
async def test_the_judgement_does_not_see_retrieved_passages():
    llm = _llm_replying("CLEAR")
    state = _state("When is maintenance scheduled?")
    state["retrieved_chunks"] = [{"text": "Standard plan ... Premium plan ... Enterprise plan"}]
    with patch.object(cs, "_get_llm", return_value=llm):
        await ambiguity_node(state)
    prompt = llm.invoke.call_args.args[0]
    assert "Premium plan" not in prompt
