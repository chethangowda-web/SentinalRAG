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


def get_engine():
    global _engine
    if _engine is None:
        url = _normalize_db_url(settings.DATABASE_URL)
        kwargs = {"echo": False}
        if url.startswith("postgresql"):
            kwargs["pool_size"] = 5
            kwargs["max_overflow"] = 10
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


async def _run_alembic_migrations() -> None:
    """Add missing columns and tables for auth support (safe, idempotent)."""
    from sqlalchemy import text as sa_text

    engine = get_engine()
    async with engine.connect() as conn:
        await conn.execute(sa_text("SELECT 1"))
        tables_result = await conn.execute(
            sa_text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        )
        existing_tables = {row[0] for row in tables_result.fetchall()}
        logger.info("Existing tables: %s", sorted(existing_tables))

        if "users" not in existing_tables:
            await conn.execute(sa_text(
                "CREATE TABLE users ("
                "id VARCHAR(36) PRIMARY KEY, "
                "name VARCHAR(255) NOT NULL, "
                "email VARCHAR(255) NOT NULL UNIQUE, "
                "password_hash VARCHAR(255) NOT NULL, "
                "created_at TIMESTAMP DEFAULT NOW(), "
                "updated_at TIMESTAMP DEFAULT NOW()"
                ")"
            ))
            await conn.execute(sa_text("CREATE INDEX IF NOT EXISTS ix_users_email ON users(email)"))
            logger.info("Created users table")

        if "evaluation_runs" not in existing_tables:
            await conn.execute(sa_text(
                "CREATE TABLE evaluation_runs ("
                "id VARCHAR(36) PRIMARY KEY, "
                "evaluation_id VARCHAR(100) NOT NULL, "
                "user_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL, "
                "status VARCHAR(20) NOT NULL DEFAULT 'running', "
                "created_at TIMESTAMP DEFAULT NOW()"
                ")"
            ))
            await conn.execute(sa_text(
                "CREATE INDEX IF NOT EXISTS ix_evaluation_runs_evaluation_id ON evaluation_runs(evaluation_id)")
            )
            await conn.execute(sa_text(
                "CREATE INDEX IF NOT EXISTS ix_evaluation_runs_user_id ON evaluation_runs(user_id)")
            )
            logger.info("Created evaluation_runs table")

        for tname in ("documents", "chat_sessions", "traces"):
            if tname in existing_tables:
                col_check = await conn.execute(
                    sa_text(
                        "SELECT EXISTS (SELECT FROM information_schema.columns "
                        "WHERE table_name = :t AND column_name = 'user_id')"
                    ),
                    {"t": tname},
                )
                has_col = col_check.scalar()
                if not has_col:
                    await conn.execute(sa_text(
                        f"ALTER TABLE {tname} ADD COLUMN user_id VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL"
                    ))
                    await conn.execute(sa_text(f"CREATE INDEX IF NOT EXISTS ix_{tname}_user_id ON {tname}(user_id)"))
                    logger.info("Added user_id column + index to %s", tname)

        await conn.execute(sa_text(
            "CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) PRIMARY KEY)"
        ))
        version_check = await conn.execute(sa_text("SELECT version_num FROM alembic_version"))
        row = version_check.fetchone()
        if not row:
            await conn.execute(sa_text("INSERT INTO alembic_version (version_num) VALUES ('003')"))
            logger.info("Stamped alembic_version at 003")

        await conn.commit()

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
            logger.warning("Alembic migration failed, fallback to create_all: %s", e)
            engine = get_engine()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Postgres tables created via create_all (fallback)")
