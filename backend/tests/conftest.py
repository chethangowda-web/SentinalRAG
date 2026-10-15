import asyncio
import os

os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

TEST_DATABASE_URL = "sqlite+aiosqlite://"

import app.core.database as db_module  # noqa: E402
from app.core.config import settings  # noqa: E402

settings.DATABASE_URL = TEST_DATABASE_URL
settings.SECRET_KEY = "test-secret-key-not-for-production"

db_module._engine = None
db_module._async_session_maker = None

from app.core.auth import get_current_user  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine):
    connection = await async_engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)

    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session):
    user = User(
        id="test-user-id",
        name="Test User",
        email="test@example.com",
        password_hash="not-a-real-hash",
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def async_client(db_session, test_user):
    # Every /api/v1 route except auth and health requires a logged-in user.
    app.dependency_overrides[get_current_user] = lambda: test_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture(autouse=True)
def no_real_llm_calls(monkeypatch):
    """CI sets a dummy API key so config validates; make sure no test can reach a real LLM with it.

    Tests that need a model patch `_get_llm` themselves, which overrides this.
    """
    for module in (
        "app.services.contradiction_service",
        "app.services.clarification_service",
        "app.services.query_rewriter",
        "app.services.answer_generator",
    ):
        monkeypatch.setattr(f"{module}._get_llm", lambda: None)


@pytest.fixture(autouse=True)
def fresh_rate_limits():
    """Auth rate limits are process-wide counters; start every test with empty ones."""
    from app.api.v1.auth import reset_rate_limits

    reset_rate_limits()
    yield
    reset_rate_limits()
