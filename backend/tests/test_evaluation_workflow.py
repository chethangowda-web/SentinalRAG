import asyncio
import json

import pytest

from evaluation.dataset import filter_dataset, load_dataset
from evaluation.services import runner as runner_module
from evaluation.services.runner import EvaluationRunner


def test_the_quick_set_covers_every_behaviour_with_far_fewer_questions():
    questions = load_dataset()
    quick = filter_dataset(questions, tags=["quick"])
    assert len(questions) == 18 and 8 <= len(quick) <= 10
    categories = {q["category"] for q in quick}
    assert {"contradictory", "missing_context", "ambiguous"} <= categories
    assert categories & {"easy", "medium", "hard"}


class _Counter:
    """Calls in flight across every fake pipeline that shares it."""

    def __init__(self):
        self.running = 0
        self.peak = 0


class _FakePipeline:
    def __init__(self, delay: float, counter: _Counter | None = None):
        self.delay = delay
        self.counter = counter or _Counter()
        self.running = 0
        self.peak = 0

    async def answer(self, question, session, user_id=None):
        for c in (self, self.counter):
            c.running += 1
            c.peak = max(c.peak, c.running)
        await asyncio.sleep(self.delay)
        for c in (self, self.counter):
            c.running -= 1
        return {
            "answer": "30 days", "confidence_score": 70.0, "confidence_level": "HIGH", "latencies": {"total": 10.0},
            "citations": [], "reasoning_path": ["retrieve", "generate_answer"], "retrieved_chunks": [],
        }


def _questions(n):
    return [{"id": str(i), "question": f"Question {i}?", "ground_truth": "30 days", "category": "easy"} for i in range(n)]


@pytest.mark.asyncio
async def test_questions_and_both_pipelines_run_at_the_same_time_and_progress_is_published(tmp_path, monkeypatch, db_session):
    status_file = tmp_path / "tasks.json"
    monkeypatch.setattr(runner_module, "_STATUS_FILE", status_file)
    monkeypatch.setattr(runner_module, "RESULTS_DIR", tmp_path)

    runner = EvaluationRunner()
    shared = _Counter()
    runner.baseline, runner.sentinel = _FakePipeline(0.05, shared), _FakePipeline(0.05, shared)
    monkeypatch.setattr(runner, "_save_result", lambda *a, **k: None)
    monkeypatch.setattr(runner, "_update_history", lambda *a, **k: None)

    result = await runner.run(db_session, questions=_questions(6), eval_id="e1")

    # Questions overlap (up to the limit), and both pipelines of a question overlap with each other
    assert runner.sentinel.peak == runner_module.QUESTION_CONCURRENCY
    assert shared.peak == 2 * runner_module.QUESTION_CONCURRENCY
    assert result["total_questions"] == 6

    task = json.loads(status_file.read_text())["e1"]
    assert task["stage"] == "scoring"
    assert [s["state"] for s in task["steps"]] == ["done"] * 6
    assert all(s["baseline"] == "done" and s["sentinel"] == "done" for s in task["steps"])
    assert task["progress"] == 6


@pytest.mark.asyncio
async def test_a_question_that_fails_is_marked_failed_and_the_rest_still_finish(tmp_path, monkeypatch, db_session):
    status_file = tmp_path / "tasks.json"
    monkeypatch.setattr(runner_module, "_STATUS_FILE", status_file)

    class Flaky(_FakePipeline):
        async def answer(self, question, session, user_id=None):
            if question == "Question 1?":
                raise RuntimeError("model unavailable")
            return await super().answer(question, session, user_id)

    runner = EvaluationRunner()
    runner.baseline, runner.sentinel = Flaky(0.01), Flaky(0.01)
    monkeypatch.setattr(runner, "_save_result", lambda *a, **k: None)
    monkeypatch.setattr(runner, "_update_history", lambda *a, **k: None)

    result = await runner.run(db_session, questions=_questions(3), eval_id="e2")

    assert result["total_questions"] == 2
    states = [s["state"] for s in json.loads(status_file.read_text())["e2"]["steps"]]
    assert states == ["done", "failed", "done"]


@pytest.mark.asyncio
async def test_a_run_where_every_question_fails_is_an_error_not_an_empty_report(tmp_path, monkeypatch, db_session):
    monkeypatch.setattr(runner_module, "_STATUS_FILE", tmp_path / "tasks.json")

    class Broken(_FakePipeline):
        async def answer(self, question, session, user_id=None):
            raise RuntimeError("meta tensor")

    runner = EvaluationRunner()
    runner.baseline, runner.sentinel = Broken(0), Broken(0)
    with pytest.raises(RuntimeError, match="No question could be answered"):
        await runner.run(db_session, questions=_questions(2), eval_id="e3")


def test_models_loaded_by_several_threads_at_once_are_loaded_only_once(monkeypatch):
    import sys
    import threading
    import time
    import types

    from app.services import reranker_service

    loads = []

    class FakeCrossEncoder:
        def __init__(self, name, device="cpu"):
            loads.append(name)
            time.sleep(0.1)  # a slow load is what lets a second thread start its own

    fake_module = types.ModuleType("sentence_transformers")
    fake_module.CrossEncoder = FakeCrossEncoder
    fake_torch = types.ModuleType("torch")
    fake_torch.set_num_threads = lambda n: None
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)
    monkeypatch.setattr(reranker_service, "_model", None)
    monkeypatch.setattr(reranker_service, "_model_name", None)

    threads = [threading.Thread(target=reranker_service._load_reranker) for _ in range(5)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(loads) == 1
