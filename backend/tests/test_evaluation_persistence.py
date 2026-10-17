import json

import pytest

from app.api.v1 import evaluation as evaluation_api
from app.models.evaluation_run import EvaluationRun
from evaluation.behaviour import behaviour_checks


def _row(category, baseline_answer, sentinel_answer, clarified=False):
    return {
        "id": "1", "question": "q", "ground_truth": "gt", "category": category,
        "baseline": {"answer": baseline_answer, "clarification_needed": False},
        "sentinel": {"answer": sentinel_answer, "clarification_needed": clarified},
    }


def _report():
    return {
        "evaluation_id": "run-1", "timestamp": "2026-10-17T10:00:00Z", "total_questions": 4, "dataset": "benchmark",
        "summary": {"baseline": {}, "sentinel": {}, "comparison": {}},
        "per_question": [
            _row("easy", "30 days.", "30 days."),
            _row("missing_context", "Probably 5G.", "I don't have enough information to answer this question."),
            _row("contradictory", "30 days.", "The documents conflict: 30 vs 45 days."),
            _row("ambiguous", "It depends.", None, clarified=True),
        ],
    }


def test_behaviour_checks_score_each_pipeline_on_what_the_category_should_produce():
    by_label = {c["label"]: c for c in behaviour_checks(_report())}
    assert by_label["Specific questions answered"]["baseline"] == 1
    refused = by_label["Unanswerable questions refused"]
    assert (refused["baseline"], refused["sentinel"], refused["total"]) == (0, 1, 1)
    conflict = by_label["Conflicting sources surfaced"]
    assert (conflict["baseline"], conflict["sentinel"]) == (0, 1)
    clarified = by_label["Vague questions clarified"]
    assert (clarified["baseline"], clarified["sentinel"]) == (0, 1)


def test_a_raw_text_fallback_does_not_count_as_an_answer():
    row = _row("easy", "Based on the retrieved documents (source: d1):\n\nraw text", "30 days.")
    easy = behaviour_checks({"per_question": [row]})[0]
    assert (easy["baseline"], easy["sentinel"]) == (0, 1)


@pytest.mark.asyncio
async def test_a_finished_report_survives_losing_the_result_file(db_session, test_user, monkeypatch):
    run = EvaluationRun(evaluation_id="run-1", user_id=test_user.id, status="completed", result_json=json.dumps(_report()))
    db_session.add(run)
    await db_session.commit()

    monkeypatch.setattr(evaluation_api._report_gen, "load_result", lambda _id: None)  # the container was replaced
    report = await evaluation_api._latest_report_for(db_session, test_user.id)

    assert report["evaluation_id"] == "run-1"
    assert len(report["behaviour"]) == 4  # computed on load, so older stored reports get it too


@pytest.mark.asyncio
async def test_history_is_rebuilt_from_stored_results(async_client, db_session, test_user, monkeypatch):
    db_session.add(EvaluationRun(evaluation_id="run-1", user_id=test_user.id, status="completed", result_json=json.dumps(_report())))
    await db_session.commit()
    monkeypatch.setattr(evaluation_api._report_gen, "load_history", lambda: [])

    history = (await async_client.get("/api/v1/evaluation/history")).json()
    assert [(h["evaluation_id"], h["total_questions"]) for h in history] == [("run-1", 4)]

    latest = (await async_client.get("/api/v1/evaluation/latest")).json()
    assert latest["report"]["evaluation_id"] == "run-1"


@pytest.mark.asyncio
async def test_no_stored_result_still_means_no_report(db_session, test_user, monkeypatch):
    db_session.add(EvaluationRun(evaluation_id="run-2", user_id=test_user.id, status="failed"))
    await db_session.commit()
    monkeypatch.setattr(evaluation_api._report_gen, "load_result", lambda _id: None)
    assert await evaluation_api._latest_report_for(db_session, test_user.id) is None
