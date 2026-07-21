import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from evaluation.dataset import load_dataset, get_dataset_summary, filter_dataset
from evaluation.metrics.base import BaseMetric, MetricCollection, MetricResult
from evaluation.metrics.ragas_metrics import (
    Faithfulness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    _get_keywords,
    _split_sentences,
)
from evaluation.metrics.deepeval_metrics import Hallucination, Bias, Toxicity, Correctness
from evaluation.metrics.custom_metrics import (
    ConfidenceCalibration,
    CitationAccuracy,
    ContradictionDetectionRate,
    RetrySuccessRate,
    ClarificationRate,
    UnsupportedAnswerRate,
    LatencyMetric,
)
from evaluation.metrics.collector import MetricsCollector
from evaluation.reports.report_generator import ReportGenerator
from evaluation.reports.visualizer import Visualizer

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_CHUNKS = [
    {"chunk_id": "c1", "document_id": "d1", "text": "The minimum uptime requirement for network services is 99.9%, measured on a monthly basis.", "page_number": 1, "section": "SLA", "filename": "sla_policy.pdf", "vector_score": 0.95, "bm25_score": 0.80, "rerank_score": 0.92},
    {"chunk_id": "c2", "document_id": "d1", "text": "If uptime falls below 99.9%, the customer receives a 5% service credit per hour of downtime, up to a maximum of 100% of the monthly fee.", "page_number": 2, "section": "Penalties", "filename": "sla_policy.pdf", "vector_score": 0.90, "bm25_score": 0.75, "rerank_score": 0.88},
    {"chunk_id": "c3", "document_id": "d2", "text": "The system accepts PDF, PNG, JPG, and JPEG files for upload.", "page_number": 1, "section": "Upload", "filename": "user_guide.pdf", "vector_score": 0.85, "bm25_score": 0.70, "rerank_score": 0.80},
]

SAMPLE_CITATIONS = [
    {"document_id": "d1", "chunk_id": "c1", "page": 1, "text": "The minimum uptime requirement for network services is 99.9%"},
    {"document_id": "d1", "chunk_id": "c2", "page": 2, "text": "If uptime falls below 99.9%"},
]

SAMPLE_QUESTIONS = [
    {
        "id": "1", "question": "What is the minimum uptime requirement?",
        "ground_truth": "The minimum uptime requirement is 99.9%.",
        "category": "easy", "has_contradiction": False,
        "needs_clarification": False, "has_context": True,
        "expected_documents": ["sla_policy.pdf"], "tags": ["uptime"],
    },
    {
        "id": "2", "question": "What is policy on 5G roaming?",
        "ground_truth": "No information available about 5G roaming.",
        "category": "missing_context", "has_contradiction": False,
        "needs_clarification": False, "has_context": False,
        "expected_documents": [], "tags": ["5g"],
    },
    {
        "id": "3", "question": "Tell me about the network",
        "ground_truth": "Too vague, please specify.",
        "category": "ambiguous", "has_contradiction": False,
        "needs_clarification": True, "has_context": True,
        "expected_documents": [], "tags": ["vague"],
    },
    {
        "id": "4", "question": "One doc says 99.9% uptime, another says 99.99%. What is correct?",
        "ground_truth": "There is a contradiction between documents.",
        "category": "contradictory", "has_contradiction": True,
        "needs_clarification": False, "has_context": True,
        "expected_documents": ["sla_policy.pdf", "premium_addendum.pdf"],
        "tags": ["uptime", "contradiction"],
    },
]


@pytest.fixture
def temp_dataset_file():
    data = SAMPLE_QUESTIONS
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def sample_result():
    return {
        "evaluation_id": "test-eval-1",
        "timestamp": "2026-07-18T12:00:00",
        "dataset": "benchmark.json",
        "total_questions": 4,
        "summary": {
            "baseline": {
                "avg_faithfulness": {"value": 0.75, "success": True, "error": None, "details": {}},
                "avg_hallucination": {"value": 0.25, "success": True, "error": None, "details": {}},
                "avg_correctness": {"value": 0.60, "success": True, "error": None, "details": {}},
                "avg_answer_relevancy": {"value": 0.70, "success": True, "error": None, "details": {}},
                "avg_context_precision": {"value": 0.65, "success": True, "error": None, "details": {}},
                "avg_context_recall": {"value": 0.55, "success": True, "error": None, "details": {}},
                "latency": {"value": 410.0, "success": True, "error": None, "details": {"average_ms": 410.0}},
            },
            "sentinel": {
                "avg_faithfulness": {"value": 0.96, "success": True, "error": None, "details": {}},
                "avg_hallucination": {"value": 0.04, "success": True, "error": None, "details": {}},
                "avg_correctness": {"value": 0.88, "success": True, "error": None, "details": {}},
                "avg_answer_relevancy": {"value": 0.92, "success": True, "error": None, "details": {}},
                "avg_context_precision": {"value": 0.90, "success": True, "error": None, "details": {}},
                "avg_context_recall": {"value": 0.85, "success": True, "error": None, "details": {}},
                "latency": {"value": 470.0, "success": True, "error": None, "details": {"average_ms": 470.0}},
            },
            "comparison": {
                "avg_faithfulness": {"baseline": 0.75, "sentinel": 0.96, "absolute_change": 0.21, "relative_change_pct": 28.0, "direction": "up", "improved": True},
                "avg_hallucination": {"baseline": 0.25, "sentinel": 0.04, "absolute_change": -0.21, "relative_change_pct": -84.0, "direction": "down", "improved": True},
            },
        },
        "per_question": [
            {
                "id": "1", "question": "What is the minimum uptime requirement?", "category": "easy",
                "ground_truth": "99.9%",
                "baseline": {"answer": "99.9%", "confidence_score": 95.0, "confidence_level": "HIGH",
                             "latencies": {"total": 400}, "citations": SAMPLE_CITATIONS[:1],
                             "reasoning_path": ["retrieve", "generate"], "contradiction_detected": False,
                             "clarification_needed": False, "clarification_question": None, "retry_count": 0},
                "sentinel": {"answer": "The requirement is 99.9% uptime.", "confidence_score": 98.0,
                             "confidence_level": "HIGH", "latencies": {"total": 450},
                             "citations": SAMPLE_CITATIONS, "reasoning_path": ["retrieve", "confidence_evaluate", "generate_answer"],
                             "contradiction_detected": False, "contradiction_reason": None,
                             "clarification_needed": False, "clarification_question": None, "retry_count": 0},
            }
        ],
        "failure_modes": {"document_missing": 1, "conflicting_documents": 1, "empty_retrieval": 0, "low_confidence": 0, "clarification_needed": 0, "contradiction_detected": 0, "errors": 0},
    }


# ---------------------------------------------------------------------------
# Dataset Tests
# ---------------------------------------------------------------------------

class TestDataset:
    def test_load_dataset(self, temp_dataset_file):
        data = load_dataset(temp_dataset_file)
        assert len(data) == 4
        assert data[0]["id"] == "1"
        assert data[0]["question"] == "What is the minimum uptime requirement?"

    def test_load_dataset_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_dataset("/nonexistent/path.json")

    def test_load_dataset_invalid_format(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            f.write('{"not": "an array"}')
            path = f.name
        with pytest.raises(ValueError, match="JSON array"):
            load_dataset(path)
        os.unlink(path)

    def test_get_dataset_summary(self):
        summary = get_dataset_summary(SAMPLE_QUESTIONS)
        assert summary["total"] == 4
        assert summary["categories"]["easy"] == 1
        assert summary["categories"]["missing_context"] == 1
        assert summary["has_contradiction"] == 1
        assert summary["needs_clarification"] == 1
        assert summary["missing_context"] == 1

    def test_filter_dataset_by_category(self):
        filtered = filter_dataset(SAMPLE_QUESTIONS, categories=["easy"])
        assert len(filtered) == 1
        assert filtered[0]["id"] == "1"

    def test_filter_dataset_by_tags(self):
        filtered = filter_dataset(SAMPLE_QUESTIONS, tags=["contradiction"])
        assert len(filtered) == 1
        assert filtered[0]["id"] == "4"

    def test_filter_dataset_limit(self):
        filtered = filter_dataset(SAMPLE_QUESTIONS, limit=2)
        assert len(filtered) == 2

    def test_filter_no_match(self):
        filtered = filter_dataset(SAMPLE_QUESTIONS, tags=["nonexistent"])
        assert len(filtered) == 0


# ---------------------------------------------------------------------------
# Metrics Base Tests
# ---------------------------------------------------------------------------

class TestMetricsBase:
    def test_metric_result_defaults(self):
        r = MetricResult(name="test", value=0.5)
        assert r.name == "test"
        assert r.value == 0.5
        assert r.details is None
        assert r.success is True
        assert r.error is None

    def test_metric_result_with_error(self):
        r = MetricResult(name="test", value=0.0, success=False, error="something broke")
        assert r.success is False
        assert r.error == "something broke"

    def test_base_metric_raises(self):
        m = BaseMetric()
        with pytest.raises(NotImplementedError):
            m.compute()

    def test_base_metric_call_wraps_exception(self):
        class BrokenMetric(BaseMetric):
            name = "broken"
            def compute(self):
                raise ValueError("fail")

        m = BrokenMetric()
        result = m()
        assert result.success is False
        assert "fail" in result.error

    def test_metric_collection(self):
        c = MetricCollection()
        c.add(MetricResult(name="a", value=1.0))
        c.add(MetricResult(name="b", value=2.0))
        assert len(c.metrics) == 2
        assert c.get("a").value == 1.0
        assert c.get("c") is None

    def test_metric_collection_to_dict(self):
        c = MetricCollection()
        c.add(MetricResult(name="x", value=0.5, details={"key": "val"}))
        d = c.to_dict()
        assert "x" in d
        assert d["x"]["value"] == 0.5
        assert d["x"]["details"]["key"] == "val"

    def test_metric_collection_successful_failed(self):
        c = MetricCollection()
        c.add(MetricResult(name="a", value=1.0, success=True))
        c.add(MetricResult(name="b", value=0.0, success=False))
        assert len(c.successful) == 1
        assert len(c.failed) == 1


# ---------------------------------------------------------------------------
# RAGAS Metrics Tests
# ---------------------------------------------------------------------------

class TestRagasMetrics:
    def test_faithfulness_fully_supported(self):
        metric = Faithfulness()
        answer = "The minimum uptime requirement is 99.9%."
        result = metric(answer=answer, chunks=SAMPLE_CHUNKS[:1])
        assert result.success
        assert result.value >= 0.5

    def test_faithfulness_partial_support(self):
        metric = Faithfulness()
        answer = "The minimum uptime requirement is 99.9%. The moon is made of cheese."
        result = metric(answer=answer, chunks=SAMPLE_CHUNKS[:1])
        assert result.value < 1.0

    def test_faithfulness_empty_answer(self):
        metric = Faithfulness()
        result = metric(answer="", chunks=SAMPLE_CHUNKS)
        assert result.value == 1.0

    def test_faithfulness_empty_chunks(self):
        metric = Faithfulness()
        result = metric(answer="Some answer.", chunks=[])
        assert result.value == 0.0

    def test_answer_relevancy_related(self):
        metric = AnswerRelevancy()
        result = metric(question="What is the uptime requirement?", answer="99.9% uptime")
        assert result.value > 0

    def test_answer_relevancy_unrelated(self):
        metric = AnswerRelevancy()
        result = metric(question="What is the uptime requirement?", answer="The weather is nice today.")
        assert result.value < 0.5

    def test_answer_relevancy_empty(self):
        metric = AnswerRelevancy()
        result = metric(question="", answer="")
        assert result.value == 0.0

    def test_context_precision_all_relevant(self):
        metric = ContextPrecision()
        chunks = SAMPLE_CHUNKS[:1]
        result = metric(chunks=chunks, ground_truth="99.9% uptime", question="uptime?")
        assert result.value > 0

    def test_context_precision_empty_chunks(self):
        metric = ContextPrecision()
        result = metric(chunks=[], ground_truth="test", question="test")
        assert result.value == 0.0

    def test_context_recall_all_retrieved(self):
        metric = ContextRecall()
        result = metric(chunks=SAMPLE_CHUNKS[:1], ground_truth="99.9% uptime", question="uptime?")
        assert result.value > 0

    def test_context_recall_empty_chunks(self):
        metric = ContextRecall()
        result = metric(chunks=[], ground_truth="test", question="test")
        assert result.value == 0.0

    def test_split_sentences(self):
        result = _split_sentences("First sentence. Second sentence! Third?")
        assert len(result) == 3

    def test_get_keywords(self):
        kws = _get_keywords("The quick brown fox jumps over the lazy dog")
        assert "the" not in kws
        assert "quick" in kws
        assert "dog" in kws
        assert len(kws) == 6


# ---------------------------------------------------------------------------
# DeepEval Metrics Tests
# ---------------------------------------------------------------------------

class TestDeepEvalMetrics:
    def test_hallucination_none(self):
        metric = Hallucination()
        answer = "The minimum uptime requirement is 99.9%."
        result = metric(answer=answer, chunks=SAMPLE_CHUNKS[:1])
        assert result.value < 0.5

    def test_hallucination_full(self):
        metric = Hallucination()
        answer = "The moon is made of cheese."
        chunks = [{"chunk_id": "c99", "text": "The uptime requirement is 99.9%."}]
        result = metric(answer=answer, chunks=chunks)
        assert result.value > 0.5

    def test_hallucination_empty_answer(self):
        metric = Hallucination()
        result = metric(answer="", chunks=SAMPLE_CHUNKS)
        assert result.value == 0.0

    def test_bias_clean(self):
        metric = Bias()
        result = metric(answer="The uptime requirement is 99.9%.")
        assert result.value == 1.0

    def test_bias_detected(self):
        metric = Bias()
        result = metric(answer="All women are bad at technology. Old people cannot learn new skills. Poor people should not get service.")
        assert result.value < 0.7

    def test_bias_empty(self):
        metric = Bias()
        result = metric(answer="")
        assert result.value == 1.0

    def test_toxicity_clean(self):
        metric = Toxicity()
        result = metric(answer="The uptime requirement is 99.9%.")
        assert result.value == 1.0

    def test_toxicity_detected(self):
        metric = Toxicity()
        result = metric(answer="This is a stupid policy and everyone hates it.")
        assert result.value < 0.8

    def test_toxicity_empty(self):
        metric = Toxicity()
        result = metric(answer="")
        assert result.value == 1.0

    def test_correctness_exact_match(self):
        metric = Correctness()
        result = metric(answer="99.9% uptime requirement", ground_truth="99.9% uptime requirement")
        assert result.value > 0.5

    def test_correctness_no_match(self):
        metric = Correctness()
        result = metric(answer="The weather is nice.", ground_truth="99.9% uptime requirement")
        assert result.value < 0.5

    def test_correctness_empty(self):
        metric = Correctness()
        result = metric(answer="", ground_truth="")
        assert result.value == 0.0


# ---------------------------------------------------------------------------
# Custom Metrics Tests
# ---------------------------------------------------------------------------

class TestCustomMetrics:
    def test_confidence_calibration_perfect(self):
        metric = ConfidenceCalibration()
        result = metric(confidence_scores=[90.0, 80.0], correctness_flags=[True, True])
        assert result.value > 0.9

    def test_confidence_calibration_poor(self):
        metric = ConfidenceCalibration()
        result = metric(confidence_scores=[90.0, 80.0], correctness_flags=[False, False])
        assert result.value < 0.5

    def test_confidence_calibration_empty(self):
        metric = ConfidenceCalibration()
        result = metric(confidence_scores=[], correctness_flags=[])
        assert result.value == 0.0

    def test_confidence_calibration_mismatched_lengths(self):
        metric = ConfidenceCalibration()
        result = metric(confidence_scores=[90.0], correctness_flags=[True, False])
        assert result.value == 0.0

    def test_citation_accuracy_all_match(self):
        metric = CitationAccuracy()
        result = metric(citations=SAMPLE_CITATIONS, chunks=SAMPLE_CHUNKS)
        assert result.value >= 0.5

    def test_citation_accuracy_empty_citations(self):
        metric = CitationAccuracy()
        result = metric(citations=[], chunks=SAMPLE_CHUNKS)
        assert result.value == 1.0

    def test_contradiction_detection_all_found(self):
        metric = ContradictionDetectionRate()
        result = metric(contradictions_exist=[True, True], contradictions_detected=[True, True])
        assert result.value == 1.0

    def test_contradiction_detection_missed(self):
        metric = ContradictionDetectionRate()
        result = metric(contradictions_exist=[True, True], contradictions_detected=[False, False])
        assert result.value == 0.0

    def test_contradiction_detection_empty(self):
        metric = ContradictionDetectionRate()
        result = metric(contradictions_exist=[], contradictions_detected=[])
        assert result.value == 1.0

    def test_retry_success_all_improved(self):
        metric = RetrySuccessRate()
        result = metric(confidence_before=[50.0, 60.0], confidence_after=[80.0, 85.0])
        assert result.value == 1.0

    def test_retry_success_none_improved(self):
        metric = RetrySuccessRate()
        result = metric(confidence_before=[80.0, 85.0], confidence_after=[70.0, 75.0])
        assert result.value == 0.0

    def test_retry_success_empty(self):
        metric = RetrySuccessRate()
        result = metric(confidence_before=[], confidence_after=[])
        assert result.value == 1.0

    def test_clarification_rate_all_correct(self):
        metric = ClarificationRate()
        result = metric(clarification_needed=[True, False], clarification_triggered=[True, False])
        assert result.value == 1.0

    def test_clarification_rate_missed(self):
        metric = ClarificationRate()
        result = metric(clarification_needed=[True], clarification_triggered=[False])
        assert result.value == 0.0

    def test_clarification_rate_empty(self):
        metric = ClarificationRate()
        result = metric(clarification_needed=[], clarification_triggered=[])
        assert result.value == 1.0

    def test_unsupported_answer_fully_supported(self):
        metric = UnsupportedAnswerRate()
        answer = "99.9% uptime requirement."
        result = metric(answer=answer, chunks=SAMPLE_CHUNKS[:1])
        assert result.value < 0.5

    def test_unsupported_answer_fully_unsupported(self):
        metric = UnsupportedAnswerRate()
        answer = "The moon is made of cheese."
        result = metric(answer=answer, chunks=SAMPLE_CHUNKS[:1])
        assert result.value > 0.5

    def test_unsupported_answer_empty_answer(self):
        metric = UnsupportedAnswerRate()
        result = metric(answer="", chunks=SAMPLE_CHUNKS)
        assert result.value == 0.0

    def test_unsupported_answer_empty_chunks(self):
        metric = UnsupportedAnswerRate()
        result = metric(answer="Some answer.", chunks=[])
        assert result.value == 1.0

    def test_latency_basic(self):
        metric = LatencyMetric()
        result = metric(latencies_ms=[100.0, 200.0, 300.0])
        assert result.value == 200.0
        assert result.details["p50_ms"] == 200.0
        assert result.details["samples"] == 3

    def test_latency_empty(self):
        metric = LatencyMetric()
        result = metric(latencies_ms=[])
        assert result.value == 0.0


# ---------------------------------------------------------------------------
# Metrics Collector Tests
# ---------------------------------------------------------------------------

class TestMetricsCollector:
    def test_compute_single(self):
        collector = MetricsCollector()
        result = collector.compute_single(
            question="What is the uptime requirement?",
            answer="99.9% uptime",
            chunks=SAMPLE_CHUNKS[:1],
            ground_truth="99.9%",
            citations=SAMPLE_CITATIONS,
            confidence_score=95.0,
            latencies={"total": 400.0, "vector_search": 100.0},
        )
        assert result.get("faithfulness") is not None
        assert result.get("answer_relevancy") is not None
        assert result.get("context_precision") is not None
        assert result.get("hallucination") is not None
        assert result.get("correctness") is not None
        assert result.get("citation_accuracy") is not None
        assert result.get("latency") is not None


# ---------------------------------------------------------------------------
# Baseline RAG & Sentinel RAG Tests (mocked)
# ---------------------------------------------------------------------------

class TestBaselineRAG:
    @pytest.mark.asyncio
    async def test_baseline_answer(self):
        from evaluation.services.baseline_rag import BaselineRAG

        mock_response = MagicMock()
        mock_response.confidence = 95.0
        mock_response.confidence_level = "HIGH"
        mock_response.latencies = {"vector_search": 50.0, "total": 400.0}

        mock_result = MagicMock()
        mock_result.chunk_id = "c1"
        mock_result.document_id = "d1"
        mock_result.text = "The minimum uptime requirement is 99.9%."
        mock_result.page_number = 1
        mock_result.section = "SLA"
        mock_result.filename = "sla_policy.pdf"
        mock_result.vector_score = 0.95
        mock_result.bm25_score = 0.80
        mock_result.rerank_score = 0.92
        mock_response.results = [mock_result]

        with patch("evaluation.services.baseline_rag.retrieve", new_callable=AsyncMock, return_value=mock_response):
            with patch("evaluation.services.baseline_rag.generate_answer", return_value="99.9% uptime"):
                rag = BaselineRAG()
                result = await rag.answer("What is the uptime?", MagicMock())

        assert result["answer"] == "99.9% uptime"
        assert result["confidence_score"] == 95.0
        assert result["confidence_level"] == "HIGH"
        assert len(result["retrieved_chunks"]) == 1
        assert "retrieve" in result["reasoning_path"]

    @pytest.mark.asyncio
    async def test_baseline_answer_error(self):
        from evaluation.services.baseline_rag import BaselineRAG

        with patch("evaluation.services.baseline_rag.retrieve", new_callable=AsyncMock, side_effect=Exception("DB error")):
            rag = BaselineRAG()
            with pytest.raises(Exception):
                await rag.answer("What is the uptime?", MagicMock())


class TestSentinelRAG:
    @pytest.mark.asyncio
    async def test_sentinel_answer(self):
        from evaluation.services.sentinel_rag import SentinelRAG

        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "question": "What is the uptime?",
            "answer": "99.9% uptime requirement",
            "confidence_score": 98.0,
            "confidence_level": "HIGH",
            "retrieved_chunks": SAMPLE_CHUNKS[:1],
            "citations": SAMPLE_CITATIONS,
            "latencies": {"retrieve_node": 100.0, "confidence_evaluate": 20.0, "generate_answer": 300.0},
            "reasoning_path": ["retrieve", "confidence_evaluate", "generate_answer"],
            "contradiction_detected": False,
            "contradiction_reason": None,
            "clarification_needed": False,
            "clarification_question": None,
            "retry_count": 0,
        }

        with patch("evaluation.services.sentinel_rag.build_graph", return_value=mock_graph):
            rag = SentinelRAG()
            result = await rag.answer("What is the uptime?", MagicMock())

        assert result["answer"] == "99.9% uptime requirement"
        assert result["confidence_score"] == 98.0
        assert result["confidence_level"] == "HIGH"
        assert result["contradiction_detected"] is False
        assert len(result["citations"]) == 2

    @pytest.mark.asyncio
    async def test_sentinel_answer_graph_error(self):
        from evaluation.services.sentinel_rag import SentinelRAG

        mock_graph = AsyncMock()
        mock_graph.ainvoke.side_effect = RuntimeError("Graph failed")

        with patch("evaluation.services.sentinel_rag.build_graph", return_value=mock_graph):
            rag = SentinelRAG()
            result = await rag.answer("What is the uptime?", MagicMock())

        assert "error" in result
        assert "Graph failed" in result["error"]


# ---------------------------------------------------------------------------
# Report Generator Tests
# ---------------------------------------------------------------------------

class TestReportGenerator:
    def test_generate_json(self, sample_result, tmp_path):
        gen = ReportGenerator(output_dir=str(tmp_path))
        files = gen.generate_all(sample_result)
        assert "json" in files
        assert Path(files["json"]).exists()
        with open(files["json"], "r") as f:
            data = json.load(f)
        assert data["evaluation_id"] == "test-eval-1"

    def test_generate_csv(self, sample_result, tmp_path):
        gen = ReportGenerator(output_dir=str(tmp_path))
        files = gen.generate_all(sample_result)
        assert "csv" in files
        assert Path(files["csv"]).exists()
        with open(files["csv"], "r") as f:
            content = f.read()
        assert "What is the minimum uptime requirement?" in content

    def test_generate_markdown(self, sample_result, tmp_path):
        gen = ReportGenerator(output_dir=str(tmp_path))
        files = gen.generate_all(sample_result)
        assert "markdown" in files
        assert Path(files["markdown"]).exists()
        with open(files["markdown"], "r") as f:
            content = f.read()
        assert "SentinelRAG Evaluation Report" in content
        assert "Faithfulness" in content

    def test_load_latest_result_not_found(self, tmp_path):
        gen = ReportGenerator(output_dir=str(tmp_path))
        result = gen.load_latest_result()
        assert result is None

    def test_load_history_empty(self, tmp_path):
        gen = ReportGenerator(output_dir=str(tmp_path))
        history = gen.load_history()
        assert history == []


# ---------------------------------------------------------------------------
# Evaluation Runner Tests (mocked)
# ---------------------------------------------------------------------------

class TestEvaluationRunner:
    @pytest.mark.asyncio
    async def test_runner_loads_dataset(self, temp_dataset_file):
        from evaluation.services.runner import EvaluationRunner

        runner = EvaluationRunner()
        data = runner._load_dataset(temp_dataset_file)
        assert len(data) == 4

    @pytest.mark.asyncio
    async def test_runner_dataset_not_found(self):
        from evaluation.services.runner import EvaluationRunner

        runner = EvaluationRunner()
        with pytest.raises(FileNotFoundError):
            runner._load_dataset("/nonexistent/path.json")

    @pytest.mark.asyncio
    async def test_runner_analyze_failure_modes(self):
        from evaluation.services.runner import EvaluationRunner

        runner = EvaluationRunner()
        per_question = [
            {"id": "1", "has_context": True, "has_contradiction": False,
             "baseline": {}, "sentinel": {"confidence_level": "HIGH", "clarification_needed": False, "contradiction_detected": False}},
            {"id": "2", "has_context": False, "has_contradiction": False,
             "baseline": {}, "sentinel": {"confidence_level": "HIGH", "clarification_needed": False, "contradiction_detected": False}},
        ]
        modes = runner._analyze_failure_modes(per_question)
        assert modes["document_missing"] == 1
        assert modes["empty_retrieval"] == 0


# ---------------------------------------------------------------------------
# Visualizer Tests
# ---------------------------------------------------------------------------

class TestVisualizer:
    def test_visualizer_import(self):
        viz = Visualizer(output_dir=tempfile.gettempdir())
        assert viz is not None


# ---------------------------------------------------------------------------
# API Tests
# ---------------------------------------------------------------------------

class TestEvaluationAPI:
    @pytest.mark.asyncio
    async def test_get_dataset_info(self, async_client):
        response = await async_client.get("/api/v1/evaluation/dataset")
        assert response.status_code in (200, 404, 500)
        if response.status_code == 200:
            data = response.json()
            assert "summary" in data
            assert "total" in data["summary"]

    @pytest.mark.asyncio
    async def test_get_evaluation_history_empty(self, async_client):
        response = await async_client.get("/api/v1/evaluation/history")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_latest_report_not_found(self, async_client):
        response = await async_client.get("/api/v1/evaluation/report")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_evaluate_endpoint(self, async_client):
        with patch("evaluation.services.runner.EvaluationRunner.run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "evaluation_id": "test-123",
                "timestamp": "2026-07-18T12:00:00",
                "total_questions": 4,
                "summary": {
                    "baseline": {},
                    "sentinel": {},
                    "comparison": {},
                },
                "failure_modes": {},
            }
            with patch("evaluation.reports.report_generator.ReportGenerator.generate_all", return_value={"json": "/tmp/test.json"}):
                with patch("evaluation.reports.visualizer.Visualizer.generate_all", return_value=[]):
                    response = await async_client.post("/api/v1/evaluate")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["evaluation_id"] == "test-123"


# ---------------------------------------------------------------------------
# Integration: Metrics Collector with mocked data
# ---------------------------------------------------------------------------

class TestMetricsIntegration:
    def test_metrics_collector_aggregate(self):
        collector = MetricsCollector()
        questions = [{"question": "What is uptime?"}, {"question": "What is refund policy?"}]
        answers = ["99.9% uptime", "30 day refund policy"]
        chunks = [[SAMPLE_CHUNKS[0]], [SAMPLE_CHUNKS[1]]]
        ground_truths = ["99.9%", "30 day refund"]
        citations = [[SAMPLE_CITATIONS[0]], [SAMPLE_CITATIONS[1]]]
        confidences = [95.0, 80.0]
        latencies = [{"total": 400.0}, {"total": 350.0}]
        contradictions_exist = [False, False]
        contradictions_detected = [False, False]
        clarifications_needed = [False, False]
        clarifications_triggered = [False, False]

        result = collector.compute_aggregate(
            all_questions=questions,
            all_answers=answers,
            all_chunks=chunks,
            all_ground_truths=ground_truths,
            all_citations=citations,
            all_confidence_scores=confidences,
            all_latencies=latencies,
            all_contradictions_exist=contradictions_exist,
            all_contradictions_detected=contradictions_detected,
            all_clarifications_needed=clarifications_needed,
            all_clarifications_triggered=clarifications_triggered,
        )

        assert result.get("avg_faithfulness") is not None
        assert result.get("avg_hallucination") is not None
        assert result.get("avg_correctness") is not None
        assert result.get("confidence_calibration") is not None
        assert result.get("contradiction_detection_rate") is not None

    def test_metrics_collector_aggregate_with_retry(self):
        collector = MetricsCollector()
        questions = [{"question": "Test"}]
        answers = ["test answer"]
        chunks = [[SAMPLE_CHUNKS[0]]]
        ground_truths = ["test"]
        citations = [[]]
        confidences = [85.0]
        latencies = [{"total": 500.0}]
        contradictions_exist = [False]
        contradictions_detected = [False]
        clarifications_needed = [False]
        clarifications_triggered = [False]

        result = collector.compute_aggregate(
            all_questions=questions,
            all_answers=answers,
            all_chunks=chunks,
            all_ground_truths=ground_truths,
            all_citations=citations,
            all_confidence_scores=confidences,
            all_latencies=latencies,
            all_contradictions_exist=contradictions_exist,
            all_contradictions_detected=contradictions_detected,
            all_clarifications_needed=clarifications_needed,
            all_clarifications_triggered=clarifications_triggered,
            confidence_before_retry=[60.0],
            confidence_after_retry=[85.0],
        )

        assert result.get("retry_success_rate") is not None
        assert result.get("retry_success_rate").value == 1.0
