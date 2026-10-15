from unittest.mock import MagicMock, patch

import pytest

from app.graph.graph_builder import build_graph
from app.graph.nodes.relevance_gate_node import OFF_TOPIC_ANSWER, relevance_gate_node, route_after_relevance_gate
from app.services import answer_generator, llm
from app.services.llm import FallbackLLM, stream_with_retry


def _chunks(*scores):
    return [{"chunk_id": f"c{i}", "document_id": "d", "text": "t", "rerank_score": s} for i, s in enumerate(scores)]


def _gate(chunks):
    return relevance_gate_node({"retrieved_chunks": chunks, "reasoning_path": [], "graph_execution": [], "latencies": {}})


# ---- relevance gate -----------------------------------------------------------------------------

def test_unrelated_question_is_answered_without_the_llm():
    update = _gate(_chunks(-11.08, -11.1))
    assert update["answer"] == OFF_TOPIC_ANSWER and update["citations"] == []
    assert update["confidence_score"] == 0.0 and update["confidence_level"] == "LOW"
    assert route_after_relevance_gate({"answer": update["answer"]}) == "end"


def test_related_or_unscored_passages_pass_the_gate():
    assert "answer" not in _gate(_chunks(-0.18, -5.3))
    assert "answer" not in _gate(_chunks(-9.0))
    assert "answer" not in _gate([{"chunk_id": "c", "text": "t"}])  # no cross-encoder scores: cannot judge
    assert "answer" not in _gate([])
    assert route_after_relevance_gate({"answer": None}) == "ambiguity_check"


def test_the_gate_can_be_switched_off(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "OFF_TOPIC_RERANK_THRESHOLD", None)
    assert "answer" not in _gate(_chunks(-11.0))


# ---- token streaming ------------------------------------------------------------------------------

def _chunk(text):
    return MagicMock(content=text)


def test_stream_with_retry_passes_each_piece_and_returns_the_whole_text():
    model = MagicMock()
    model.stream.return_value = iter([_chunk("30 "), _chunk("days"), _chunk("")])
    seen = []
    assert stream_with_retry(model, "q", seen.append) == "30 days"
    assert seen == ["30 ", "days"]


def test_stream_retries_before_any_text_but_not_after():
    rate = Exception("Error code: 429 - retry in 1s")
    first = MagicMock()
    first.stream.side_effect = [rate, iter([_chunk("ok")])]
    with patch("app.services.llm.time.sleep"):
        assert stream_with_retry(first, "q", lambda t: None) == "ok"

    def half_then_fail(_):
        yield _chunk("partial")
        raise rate

    second = MagicMock()
    second.stream.side_effect = half_then_fail
    with patch("app.services.llm.time.sleep"), pytest.raises(Exception, match="429"):
        stream_with_retry(second, "q", lambda t: None)


def test_fallback_pool_streams_from_the_next_model_when_one_is_out_of_quota(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(settings, "GEMINI_MODEL", "m1")
    monkeypatch.setattr(settings, "GEMINI_FALLBACK_MODELS", "m2")
    llm.reset_exhausted()
    first, second = MagicMock(), MagicMock()
    first.stream.side_effect = Exception("Error code: 429 - quota. Please retry in 6h30m2.3s.")
    second.stream.return_value = iter([_chunk("from m2")])
    assert "".join(c.content for c in FallbackLLM({"m1": first, "m2": second}).stream("q")) == "from m2"
    llm.reset_exhausted()


def test_generate_answer_streams_and_caches():
    answer_generator.clear_answer_cache()
    model = MagicMock()
    model.stream.return_value = iter([_chunk("30 days "), _chunk("[Source 1].")])
    chunks = [{"chunk_id": "c1", "document_id": "d1", "text": "Refunds within 30 days."}]
    seen = []
    with patch.object(answer_generator, "_get_llm", return_value=model):
        assert answer_generator.generate_answer("Refund window?", chunks, seen.append) == "30 days [Source 1]."
        again = []
        assert answer_generator.generate_answer("Refund window?", chunks, again.append) == "30 days [Source 1]."
    assert seen == ["30 days ", "[Source 1]."] and again == ["30 days [Source 1]."]
    assert model.stream.call_count == 1
    answer_generator.clear_answer_cache()


@pytest.mark.asyncio
async def test_tokens_written_in_a_worker_thread_reach_the_graph_stream():
    def fake_generate(question, chunks, on_token=None):
        for piece in ("Hello ", "world"):
            on_token(piece)
        return "Hello world"

    state = {"question": "Hi", "document_id": None, "retrieved_chunks": [{"chunk_id": "c", "text": "t", "rerank_score": 3.0}],
             "reasoning_path": [], "graph_execution": [], "latencies": {}, "retry_count": 0}
    from app.graph.nodes.generation_node import generation_node
    from langgraph.graph import END, StateGraph
    from app.graph.state import GraphState

    wf = StateGraph(GraphState)
    wf.add_node("generate_answer", generation_node)
    wf.set_entry_point("generate_answer")
    wf.add_edge("generate_answer", END)
    graph = wf.compile()

    modes = []
    with patch("app.graph.nodes.generation_node.generate_answer", side_effect=fake_generate):
        async for mode, data in graph.astream(state, stream_mode=["updates", "custom"]):
            modes.append((mode, data.get("token") if mode == "custom" else None))
    assert [t for m, t in modes if m == "custom"] == ["Hello ", "world"]
    assert modes[-1][0] == "updates"


def test_the_graph_has_the_gate_between_retrieval_and_the_ambiguity_check():
    nodes = build_graph().get_graph().nodes
    assert "relevance_gate" in nodes
