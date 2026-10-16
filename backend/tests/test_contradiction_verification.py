from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.graph.nodes.clarification_node import route_after_clarification
from app.services import contradiction_service as cs

# Both chunks contain different numbers next to a policy term, which the keyword screen flags.
CONFLICTING = [
    {"text": "The refund period is 30 days from purchase."},
    {"text": "The refund period is 14 days for hardware."},
]


def _llm_replying(text: str):
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=text)
    return llm


def test_keyword_hit_is_kept_when_no_question_is_given():
    detected, reason = cs.detect_contradictions(CONFLICTING)
    assert detected is True and reason


def test_llm_can_reject_a_keyword_false_positive():
    with patch.object(cs, "_get_llm", return_value=_llm_replying("NO")):
        assert cs.detect_contradictions(CONFLICTING, question="How long is the refund period?") == (False, None)


def test_llm_confirmation_keeps_the_contradiction():
    with patch.object(cs, "_get_llm", return_value=_llm_replying("YES")):
        detected, _ = cs.detect_contradictions(CONFLICTING, question="How long is the refund period?")
    assert detected is True


@pytest.mark.parametrize("reply", ["maybe", ""])
def test_unclear_reply_falls_back_to_the_keyword_result(reply):
    with patch.object(cs, "_get_llm", return_value=_llm_replying(reply)):
        assert cs.verify_contradiction("q", CONFLICTING, "r") is None
        detected, _ = cs.detect_contradictions(CONFLICTING, question="q")
    assert detected is True


def test_llm_failure_falls_back_to_the_keyword_result():
    llm = MagicMock()
    llm.invoke.side_effect = RuntimeError("network down")
    with patch.object(cs, "_get_llm", return_value=llm):
        detected, _ = cs.detect_contradictions(CONFLICTING, question="q")
    assert detected is True


def test_no_llm_falls_back_to_the_keyword_result():
    with patch.object(cs, "_get_llm", return_value=None):
        detected, _ = cs.detect_contradictions(CONFLICTING, question="q")
    assert detected is True


def test_no_keyword_hit_never_calls_the_llm():
    llm = _llm_replying("YES")
    with patch.object(cs, "_get_llm", return_value=llm):
        assert cs.detect_contradictions([{"text": "Alpha"}, {"text": "Beta"}], question="q") == (False, None)
    llm.invoke.assert_not_called()


def test_clarification_ends_only_when_a_question_was_asked():
    assert route_after_clarification({"clarification_needed": True}) == "end"
    assert route_after_clarification({"clarification_needed": False}) == "generate_answer"
    assert route_after_clarification({}) == "generate_answer"


@pytest.mark.asyncio
async def test_false_positive_contradiction_no_longer_blocks_the_answer(db_session):
    """Regression: a retried question whose chunks tripped the keyword check used to end with no answer."""
    from app.graph.graph_builder import build_graph

    response = MagicMock()
    response.confidence = 53.0
    response.confidence_level = "MEDIUM"
    response.latencies = {"total": 10.0}
    response.results = [
        MagicMock(
            chunk_id=f"c{i}", document_id="d1", text=text, page_number=1, section=None, filename="p.pdf",
            vector_score=0.3, bm25_score=0.0, fusion_score=0.1, rerank_score=score,
        )
        for i, (text, score) in enumerate(
            [(CONFLICTING[0]["text"], -4.0), (CONFLICTING[1]["text"], -5.0), ("Unrelated text.", -6.0)]
        )
    ]

    state = {
        "question": "How long is the refund period?", "rewritten_question": None, "document_id": None,
        "retrieved_chunks": [], "confidence_score": 0.0, "confidence_level": "LOW", "confidence_reason": None,
        "retry_count": 0, "max_retries": 2, "contradiction_detected": False, "contradiction_reason": None,
        "clarification_needed": False, "clarification_question": None, "answer": None, "citations": [],
        "reasoning_path": [], "latencies": {}, "trace_id": "t", "graph_execution": [], "retrieval_details": [],
        "confidence_breakdown": None, "llm_observability": None,
    }

    with patch("app.graph.nodes.retrieve_node.retrieve", new_callable=AsyncMock, return_value=response), \
            patch("app.graph.nodes.retry_node.retrieve", new_callable=AsyncMock, return_value=response), \
            patch("app.graph.nodes.rewrite_node.rewrite_query", return_value="refund period"), \
            patch.object(cs, "_get_llm", return_value=_llm_replying("NO")), \
            patch("app.services.clarification_service._get_llm", return_value=None), \
            patch("app.graph.nodes.generation_node.generate_answer", return_value="The refund period is 30 days."):
        result = await build_graph().ainvoke(state, {"configurable": {"db": db_session}})

    assert result["answer"] == "The refund period is 30 days."
    assert result["contradiction_detected"] is False
    assert "contradiction_detect" in result["reasoning_path"]
    assert result["reasoning_path"][-1] == "generate_answer"


@pytest.mark.asyncio
async def test_confirmed_contradiction_without_ambiguity_still_gets_an_answer(db_session):
    from app.graph.graph_builder import build_graph

    response = MagicMock()
    response.confidence = 53.0
    response.confidence_level = "MEDIUM"
    response.latencies = {"total": 10.0}
    response.results = [
        MagicMock(
            chunk_id=f"c{i}", document_id="d1", text=c["text"], page_number=1, section=None, filename="p.pdf",
            vector_score=0.3, bm25_score=0.0, fusion_score=0.1, rerank_score=score,
        )
        for i, (c, score) in enumerate(zip(CONFLICTING, [-4.0, -6.0]))
    ]
    state = {
        "question": "How long is the refund period?", "rewritten_question": None, "document_id": None,
        "retrieved_chunks": [], "confidence_score": 0.0, "confidence_level": "LOW", "confidence_reason": None,
        "retry_count": 0, "max_retries": 2, "contradiction_detected": False, "contradiction_reason": None,
        "clarification_needed": False, "clarification_question": None, "answer": None, "citations": [],
        "reasoning_path": [], "latencies": {}, "trace_id": "t", "graph_execution": [], "retrieval_details": [],
        "confidence_breakdown": None, "llm_observability": None,
    }

    with patch("app.graph.nodes.retrieve_node.retrieve", new_callable=AsyncMock, return_value=response), \
            patch("app.graph.nodes.retry_node.retrieve", new_callable=AsyncMock, return_value=response), \
            patch("app.graph.nodes.rewrite_node.rewrite_query", return_value="refund period"), \
            patch.object(cs, "_get_llm", return_value=_llm_replying("YES")), \
            patch("app.services.clarification_service._get_llm", return_value=None), \
            patch("app.graph.nodes.generation_node.generate_answer", return_value="The sources disagree: 30 vs 14 days."):
        result = await build_graph().ainvoke(state, {"configurable": {"db": db_session}})

    assert result["contradiction_detected"] is True
    assert result["answer"] == "The sources disagree: 30 vs 14 days."
    assert result["reasoning_path"][-2:] == ["clarification", "generate_answer"]
