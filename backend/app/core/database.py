import asyncio
import logging
from typing import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)

_engine = None
_async_session_maker = None


def _normalize_db_url(url: str) -> str:
    if not url:
        return url
    if url.startswith("sqlite"):
        if "+" not in url:
            url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        return url
    if url.startswith("postgresql"):
        if "+" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        parsed = urlparse(url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        sslmode = qs.pop("sslmode", None)
        if sslmode:
            ssl_value = sslmode[0].lower()
            if ssl_value == "require":
                qs["ssl"] = "require"
            elif ssl_value == "disable":
                qs["ssl"] = "disable"
        new_query = urlencode(qs, doseq=True)
        url = urlunparse(parsed._replace(query=new_query))
        return url
    return url


def get_migration_database_url() -> str:
    """The URL Alembic connects with: the same driver-qualified URL the app engine uses.

    Hosts such as Railway provide a bare postgresql:// URL; handing that to SQLAlchemy
    selects the sync psycopg2 driver, which is not installed.
    """
    return _normalize_db_url(settings.DATABASE_URL)


def get_engine():
    global _engine
    if _engine is None:
        url = _normalize_db_url(settings.DATABASE_URL)
        kwargs = {"echo": False}
        if url.startswith("postgresql"):
            # A chat answer holds its connection while the model writes (several seconds), so the pool must be
            # larger than the number of questions in flight. Postgres allows ~100 connections.
            kwargs["pool_size"] = 10
            kwargs["max_overflow"] = 20
            kwargs["pool_timeout"] = 20
            kwargs["pool_pre_ping"] = True  # a connection dropped while idle is replaced instead of failing a request
            kwargs["pool_recycle"] = 1800
            ssl_mode = settings.DATABASE_SSL
            if ssl_mode and ssl_mode.lower() not in ("disable", ""):
                connect_args = kwargs.get("connect_args", {})
                connect_args["ssl"] = ssl_mode
                kwargs["connect_args"] = connect_args
            # Check if SSL is already in URL
            if "ssl=require" in url or "ssl=required" in url:
                connect_args = kwargs.get("connect_args", {})
                connect_args.setdefault("ssl", "require")
                kwargs["connect_args"] = connect_args
        logger.info(
            "Initializing engine: provider=%s ssl=%s url=%s",
            "postgresql" if url.startswith("postgresql") else "sqlite",
            kwargs.get("connect_args", {}).get("ssl", "disabled"),
            settings.database_display_url,
        )
        _engine = create_async_engine(url, **kwargs)
    return _engine


def get_session_maker():
    global _async_session_maker
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_maker


def reset_engine():
    global _engine, _async_session_maker
    if _engine:
        try:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(_engine.dispose())
                else:
                    loop.run_until_complete(_engine.dispose())
            except RuntimeError:
                pass
        except Exception:
            pass
    _engine = None
    _async_session_maker = None


def switch_to_sqlite():
    settings.DATABASE_URL = "sqlite+aiosqlite:///./sentinelrag.db"
    settings.DATABASE_SSL = "disable"
    reset_engine()
    logger.info("Switched to SQLite as fallback database")


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


# Schema state of databases that predate Alembic (built by create_all or the old
# hand-written startup SQL). They are stamped here, then upgraded to head.
_PRE_ALEMBIC_REVISION = "902bc76d113c"


def _alembic_config():
    from pathlib import Path

    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parents[2]
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "migrations"))
    cfg.attributes["configure_logger"] = False
    return cfg


async def _run_alembic_migrations() -> None:
    """Bring the PostgreSQL schema to the latest Alembic revision."""
    from alembic import command
    from sqlalchemy import inspect as sa_inspect

    def _inspect_tables(sync_conn) -> set[str]:
        return set(sa_inspect(sync_conn).get_table_names())

    async with get_engine().connect() as conn:
        existing_tables = await conn.run_sync(_inspect_tables)
    logger.info("Existing tables: %s", sorted(existing_tables))

    cfg = _alembic_config()
    # Alembic's env.py drives its own event loop, so run it off this one.
    if "documents" in existing_tables and "alembic_version" not in existing_tables:
        logger.info("Database predates Alembic; stamping at %s", _PRE_ALEMBIC_REVISION)
        await asyncio.to_thread(command.stamp, cfg, _PRE_ALEMBIC_REVISION)
    await asyncio.to_thread(command.upgrade, cfg, "head")
    logger.info("Schema migration applied successfully")


async def init_db() -> None:
    if settings.DATABASE_URL.startswith("sqlite"):
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("SQLite tables created via create_all")
    else:
        try:
            await _run_alembic_migrations()
        except Exception as e:
            logger.exception("Alembic migration failed, falling back to create_all: %s", e)
            engine = get_engine()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Postgres tables created via create_all (fallback)")
