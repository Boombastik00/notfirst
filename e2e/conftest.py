import asyncio
import hashlib
import secrets
import threading
import uuid

import asyncpg
import pytest
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:3000"
# дев-база из docker compose опубликована на 127.0.0.1
DATABASE_DSN = "postgresql://notfirst:notfirst@127.0.0.1:5432/notfirst"

# отдельная сущность для e2e чтобы не трогать живые аккаунты
E2E_IDENTITY_EMAIL = "e2e-creator@example.com"
E2E_DISPLAY_NAME = "еядва"


def _skip_if_site_down():
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/v1/health", timeout=3) as r:
            assert r.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        pytest.skip("сайт не поднят (docker compose up), e2e пропускаются")


def _run(coro):
    """выполняет корутину в отдельном потоке: playwright уже занял loop
    главного потока и asyncio.run оттуда падает"""
    outcome = {"error": None}

    def worker():
        try:
            outcome["value"] = asyncio.run(coro)
        except BaseException as e:  # noqa: BLE001 - пробрасываем наверх целиком
            outcome["error"] = e

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    if outcome["error"] is not None:
        raise outcome["error"]
    if "value" not in outcome:
        raise RuntimeError("async-вызов не завершился")
    return outcome["value"]


async def _db():
    return await asyncpg.connect(DATABASE_DSN)


async def _ensure_e2e_user() -> uuid.UUID:
    """создаёт (или находит) e2e-аккаунт с ролью админа и возвращает id"""
    db = await _db()
    try:
        row = await db.fetchrow(
            "select user_id from auth_identities where email = $1",
            E2E_IDENTITY_EMAIL,
        )
        if row is None:
            user_id = uuid.uuid4()
            await db.execute(
                "insert into users (id, role) values ($1, 'admin')", user_id
            )
            await db.execute(
                "insert into auth_identities (user_id, provider, provider_sub, email)"
                " values ($1, 'google', $2, $3)",
                user_id,
                f"e2e-sub-{secrets.token_hex(8)}",
                E2E_IDENTITY_EMAIL,
            )
            await db.execute(
                "insert into user_profiles (user_id, display_name) values ($1, $2)",
                user_id,
                E2E_DISPLAY_NAME,
            )
            return user_id
        return row["user_id"]
    finally:
        await db.close()


async def _create_session(user_id: uuid.UUID) -> str:
    """печатает сессию с токеном и возвращает сырой токен"""
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    db = await _db()
    try:
        await db.execute(
            "insert into sessions (id, token_hash, user_id, user_agent, expires_at)"
            " values ($1, $2, $3, 'e2e', now() + interval '2 hours')",
            uuid.uuid4(),
            token_hash,
            user_id,
        )
        return token
    finally:
        await db.close()


async def _cleanup_session(token: str) -> None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    db = await _db()
    try:
        await db.execute("delete from sessions where token_hash = $1", token_hash)
    finally:
        await db.close()


@pytest.fixture(scope="session")
def site_up():
    _skip_if_site_down()
    yield


@pytest.fixture(scope="session")
def e2e_token(site_up):
    token = _run(_create_session(_run(_ensure_e2e_user())))
    yield token
    _run(_cleanup_session(token))


@pytest.fixture(scope="session")
def page_ctx():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def guest_page(page_ctx, site_up):
    context = page_ctx.new_context()
    page = context.new_page()
    yield page
    context.close()


@pytest.fixture
def authed_page(page_ctx, e2e_token):
    context = page_ctx.new_context()
    # cookie ставим до первого запроса
    context.add_cookies(
        [
            {
                "name": "nf_session",
                "value": e2e_token,
                "url": BASE_URL,
            }
        ]
    )
    page = context.new_page()
    yield page
    context.close()
