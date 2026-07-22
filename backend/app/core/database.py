import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)

_engine = None
_async_session_maker = None


def _normalize_db_url(url: str) -> str:
    if url.startswith("sqlite"):
        if "+" not in url:
            url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
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
            if ssl_mode and ssl_mode.lower() != "disable":
                kwargs["connect_args"] = {"ssl": ssl_mode}
        _engine = create_async_engine(url, **kwargs)
    return _engine


def get_session_maker():
    global _async_session_maker
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _async_session_maker


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")
