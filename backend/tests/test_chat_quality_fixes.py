from unittest.mock import MagicMock, patch

import pytest

from app.graph.nodes.ambiguity_node import ambiguity_node
from app.graph.nodes.generation_node import generation_node
from app.services import followup_service

CHUNKS = [
    {"chunk_id": "c1", "document_id": "d1", "filename": "refund_policy.pdf", "text": "Refunds within 30 days."},
    {"chunk_id": "c2", "document_id": "d2", "filename": "sla_policy.pdf", "text": "Uptime is 99.9%."},
]


def _state(question, **extra):
    return {"question": question, "reasoning_path": [], "graph_execution": [], "latencies": {},
            "retrieved_chunks": CHUNKS, **extra}


@pytest.mark.asyncio
async def test_a_question_naming_a_document_is_not_sent_to_the_ambiguity_check():
    with patch("app.graph.nodes.ambiguity_node.detect_ambiguity") as detect:
        update = await ambiguity_node(_state("What is the refund policy?"))
    detect.assert_not_called()
    assert "clarification_needed" not in update


@pytest.mark.asyncio
async def test_a_generic_word_alone_does_not_count_as_naming_a_document():
    with patch("app.graph.nodes.ambiguity_node.detect_ambiguity", return_value="Which policy?") as detect:
        update = await ambiguity_node(_state("Tell me about the policy"))
    detect.assert_called_once()
    assert update["clarification_needed"] is True


@pytest.mark.asyncio
async def test_a_question_resolved_from_the_conversation_skips_the_check():
    with patch("app.graph.nodes.ambiguity_node.detect_ambiguity") as detect:
        update = await ambiguity_node(_state("What exceptions apply to refund requests?", context_resolved=True))
    detect.assert_not_called()
    assert "conversation" in update["graph_execution"][0]["output"]


def test_followup_is_rewritten_using_history_and_long_questions_are_left_alone():
    model = MagicMock()
    model.invoke.return_value = MagicMock(content="Are there any exceptions to the 30-day refund window?")
    history = [("user", "How many days to request a refund?"), ("assistant", "30 days [Source 1].")]
    with patch.object(followup_service, "_get_llm", return_value=model):
        assert followup_service.standalone_question("And any exceptions?", history).startswith("Are there")
        assert followup_service.standalone_question("And any exceptions?", []) is None
        assert followup_service.standalone_question("word " * 20, history) is None
    assert model.invoke.call_count == 1


def test_a_failed_followup_rewrite_falls_back_to_the_original_question():
    model = MagicMock()
    model.invoke.side_effect = Exception("Error code: 500")
    with patch.object(followup_service, "_get_llm", return_value=model), \
         patch("app.services.llm.time.sleep"):
        assert followup_service.standalone_question("And exceptions?", [("user", "x")]) is None


@pytest.mark.asyncio
async def test_a_refusal_has_no_citations_and_low_confidence():
    with patch("app.graph.nodes.generation_node.generate_answer",
               return_value="I don't have enough information to answer this question."):
        update = await generation_node(_state("Capital of France?", confidence_score=77.8))
    assert update["citations"] == []
    assert update["confidence_score"] == 20.0 and update["confidence_level"] == "LOW"


@pytest.mark.asyncio
async def test_citations_are_limited_to_the_passages_the_answer_uses():
    with patch("app.graph.nodes.generation_node.generate_answer", return_value="30 days [Source 1]."):
        update = await generation_node(_state("Refund window?", confidence_score=80.0))
    assert [c["chunk_id"] for c in update["citations"]] == ["c1"]
    assert "confidence_score" not in update
