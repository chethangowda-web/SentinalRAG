"""Run the real Alembic chain against PostgreSQL.

Skipped unless MIGRATION_TEST_DATABASE_URL points at a *disposable* PostgreSQL
database: every test drops and recreates the public schema.
"""
import logging
import os

import pytest
from sqlalchemy import text

import app.core.database as db
from app.core.config import settings
from app.core.database import Base, _run_alembic_migrations

PG_URL = os.environ.get("MIGRATION_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(not PG_URL, reason="MIGRATION_TEST_DATABASE_URL not set")

HEAD = "004"


@pytest.fixture
async def pg(monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", PG_URL)
    await _dispose()
    async with db.get_engine().begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    yield db.get_engine()
    await _dispose()


async def _dispose():
    if db._engine is not None:
        await db._engine.dispose()
    db._engine = None
    db._async_session_maker = None


async def _scalar(engine, sql):
    async with engine.connect() as conn:
        return (await conn.execute(text(sql))).scalar()


async def _assert_at_head(engine):
    assert await _scalar(engine, "SELECT version_num FROM alembic_version") == HEAD
    assert await _scalar(
        engine,
        "SELECT 1 FROM information_schema.columns WHERE table_name='chunks' AND column_name='updated_at'",
    ) == 1


async def test_fresh_database_reaches_head_and_is_idempotent(pg):
    await _run_alembic_migrations()
    await _assert_at_head(pg)
    await _run_alembic_migrations()
    await _assert_at_head(pg)


async def test_database_created_by_create_all_is_stamped_and_upgraded(pg):
    async with pg.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _run_alembic_migrations()
    await _assert_at_head(pg)


@pytest.mark.parametrize("version", ["001", "902bc76d113c"])
async def test_existing_schema_at_an_old_revision_upgrades(pg, version):
    async with pg.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) PRIMARY KEY)"))
        await conn.execute(text("INSERT INTO alembic_version VALUES (:v)"), {"v": version})
    await _run_alembic_migrations()
    await _assert_at_head(pg)


async def test_migrations_do_not_disable_application_loggers(pg):
    app_logger = logging.getLogger("app.core.database")
    await _run_alembic_migrations()
    assert not app_logger.disabled
