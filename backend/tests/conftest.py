import asyncio
import os
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.main import app

BACKEND_DIR = Path(__file__).resolve().parents[1]

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://notfirst:notfirst@127.0.0.1:5432/notfirst_test",
)
SERVER_URL = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"


@pytest.fixture(autouse=True)
def _rate_limit_off():
    # лимиты проверяются отдельным тестом, остальным они только мешают
    from app.rate_limit import limiter

    limiter.enabled = False
    limiter.reset()
    yield
    limiter.enabled = False
    limiter.reset()


@pytest.fixture
def fake_google(monkeypatch):
    # подменяет обмен кода на данные аккаунта чтобы не ходить в реальный google
    from app.services.auth import GoogleUserInfo

    def _set(
        sub="sub-test",
        email="test@example.com",
        name="Тестовая Пользовательница",
        verified=True,
    ):
        info = GoogleUserInfo(sub=sub, email=email, name=name, email_verified=verified)

        async def fake_exchange(request):
            return info

        monkeypatch.setattr("app.api.v1.endpoints.auth.exchange_code", fake_exchange)

    return _set


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


async def _reset_database() -> None:
    from sqlalchemy import text

    engine = create_async_engine(SERVER_URL, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as conn:
            await conn.execute(text("DROP DATABASE IF EXISTS notfirst_test WITH (FORCE)"))
            await conn.execute(text("CREATE DATABASE notfirst_test"))
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def prepared_db():
    # интеграционные тесты живут в отдельной базе notfirst_test
    try:
        asyncio.run(_reset_database())
    except Exception as exc:  # postgres может быть недоступен без docker
        pytest.skip(f"postgres недоступен: {exc}")

    from alembic.config import Config

    from alembic import command

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(cfg, "head")

    from app.seed import run as seed_run

    asyncio.run(seed_run(TEST_DATABASE_URL))


@pytest_asyncio.fixture
async def db_session(prepared_db):
    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def api_client(prepared_db, monkeypatch):
    from httpx2 import ASGITransport, AsyncClient

    import app.core.db as core_db
    from app.core.db import get_db

    engine = create_async_engine(TEST_DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    # гейт админки ходит в базу мимо dependencies поэтому подменяем фабрику сессий
    monkeypatch.setattr(core_db, "session_factory", factory)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
    app.dependency_overrides.clear()
    await engine.dispose()
