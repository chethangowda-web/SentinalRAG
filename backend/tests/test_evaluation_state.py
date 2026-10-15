from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.api.v1 import evaluation as eval_module
from app.models.document import Document
from app.models.evaluation_run import EvaluationRun
from app.services import benchmark_service
from app.services.benchmark_service import benchmark_status, corpus_filenames


def _run(eval_id: str, user_id: str, status: str, created=None) -> EvaluationRun:
    run = EvaluationRun(evaluation_id=eval_id, user_id=user_id, status=status)
    if created is not None:
        run.created_at = created
    return run


def test_the_benchmark_corpus_is_in_the_repo():
    names = corpus_filenames()
    assert len(names) == 6 and "sla_policy.pdf" in names


@pytest.mark.asyncio
async def test_latest_never_404s_for_a_new_user_and_reports_missing_documents(async_client):
    r = await async_client.get("/api/v1/evaluation/latest")
    assert r.status_code == 200
    body = r.json()
    assert body["report"] is None and body["run"] is None
    assert body["benchmark"]["ready"] is False
    assert {d["status"] for d in body["benchmark"]["documents"]} == {"missing"}


@pytest.mark.asyncio
async def test_latest_reports_a_run_in_flight_so_a_reload_can_resume(async_client, db_session, test_user):
    db_session.add(_run("run-1", test_user.id, "running"))
    await db_session.commit()
    with patch.object(eval_module, "_load_tasks", return_value={"run-1": {"progress": 7, "total": 18, "error": None}}):
        body = (await async_client.get("/api/v1/evaluation/latest")).json()
    assert body["run"] == {"evaluation_id": "run-1", "status": "running", "progress": 7, "total": 18, "error": None}


@pytest.mark.asyncio
async def test_latest_serves_the_users_last_finished_report(async_client, db_session, test_user):
    db_session.add(_run("done-1", test_user.id, "completed"))
    await db_session.commit()
    with patch.object(eval_module._report_gen, "load_result", return_value={"evaluation_id": "done-1", "summary": {}}):
        body = (await async_client.get("/api/v1/evaluation/latest")).json()
    assert body["report"]["evaluation_id"] == "done-1"


@pytest.mark.asyncio
async def test_benchmark_is_ready_only_when_every_sample_document_is_indexed(db_session, test_user):
    names = corpus_filenames()
    for i, name in enumerate(names[:-1]):
        db_session.add(Document(id=f"d{i}", filename=name, file_type="pdf", status="embedded", user_id=test_user.id))
    await db_session.commit()
    assert (await benchmark_status(db_session, test_user.id))["ready"] is False

    db_session.add(Document(id="last", filename=names[-1], file_type="pdf", status="embedded", user_id=test_user.id))
    await db_session.commit()
    assert (await benchmark_status(db_session, test_user.id))["ready"] is True


@pytest.mark.asyncio
async def test_benchmark_status_ignores_other_users_documents(db_session):
    db_session.add(Document(id="theirs", filename=corpus_filenames()[0], file_type="pdf", status="embedded", user_id="someone-else"))
    await db_session.commit()
    status = await benchmark_status(db_session, "test-user-id")
    assert status["ready"] is False and all(d["status"] == "missing" for d in status["documents"])


@pytest.mark.asyncio
async def test_setup_starts_loading_once(async_client):
    with patch("app.api.v1.evaluation.start_loading", return_value=True) as start:
        r = await async_client.post("/api/v1/evaluation/benchmark/setup")
    assert r.status_code == 202 and r.json()["loading"] is True
    start.assert_called_once_with("test-user-id")


@pytest.mark.asyncio
async def test_evaluate_is_refused_until_the_sample_documents_are_loaded(async_client):
    r = await async_client.post("/api/v1/evaluate")
    assert r.status_code == 409 and "sample documents" in r.json()["detail"]


@pytest.mark.asyncio
async def test_evaluate_is_refused_while_a_run_is_in_flight(async_client, db_session, test_user):
    db_session.add(_run("busy", test_user.id, "running", datetime.now(timezone.utc).replace(tzinfo=None)))
    await db_session.commit()
    ready = {"ready": True, "loading": False, "documents": []}
    with patch("app.api.v1.evaluation.benchmark_status", new_callable=AsyncMock, return_value=ready):
        r = await async_client.post("/api/v1/evaluate")
    assert r.status_code == 409 and "already running" in r.json()["detail"]


@pytest.mark.asyncio
async def test_a_stale_running_row_does_not_block_a_new_run(async_client, db_session, test_user):
    old = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
    db_session.add(_run("stale", test_user.id, "running", old))
    await db_session.commit()
    ready = {"ready": True, "loading": False, "documents": []}
    with patch("app.api.v1.evaluation.benchmark_status", new_callable=AsyncMock, return_value=ready), \
            patch("app.api.v1.evaluation._run_evaluation_background", new_callable=AsyncMock):
        r = await async_client.post("/api/v1/evaluate")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_restart_recovery_completes_runs_that_have_results_and_fails_the_rest(db_session, test_user):
    db_session.add(_run("has-file", test_user.id, "running"))
    db_session.add(_run("no-file", test_user.id, "running"))
    await db_session.commit()
    with patch.object(eval_module._report_gen, "load_result", side_effect=lambda i: {"x": 1} if i == "has-file" else None):
        assert await eval_module.recover_interrupted_runs(db_session) == 2
    statuses = {r.evaluation_id: r.status for r in (await db_session.execute(select(EvaluationRun))).scalars().all()}
    assert statuses == {"has-file": "completed", "no-file": "failed"}


def test_only_one_load_runs_per_user(monkeypatch):
    monkeypatch.setattr(benchmark_service, "_loading_users", {"u1"})
    assert benchmark_service.start_loading("u1") is False
