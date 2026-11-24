from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.core.security import SESSION_COOKIE, hash_token, new_session_token
from app.models import AuthIdentity, User, UserSession
from app.services.auth import GOOGLE_PROVIDER

pytestmark = pytest.mark.asyncio


async def _test_user_id(session, sub: str):
    # id аккаунта по google-sub, поля входа теперь в отдельной таблице
    return (
        await session.execute(
            select(AuthIdentity.user_id).where(
                AuthIdentity.provider == GOOGLE_PROVIDER,
                AuthIdentity.provider_sub == sub,
            )
        )
    ).scalar_one()


async def login(api_client, sub="sub-test", email="test@example.com"):
    resp = await api_client.get("/api/v1/auth/google/callback")
    assert resp.status_code == 302
    return resp


async def test_me_without_cookie_returns_401(api_client):
    resp = await api_client.get("/api/v1/auth/me")

    assert resp.status_code == 401


async def test_start_without_google_config_returns_503(api_client, monkeypatch):
    from app.core.config import get_settings

    # независимость от окружения: в терминале могут быть экспортированы настоящие ключи
    monkeypatch.setattr(get_settings(), "google_client_id", "")
    resp = await api_client.get("/api/v1/auth/google/start")

    assert resp.status_code == 503


async def test_full_login_flow(api_client, db_session, fake_google):
    fake_google()
    resp = await login(api_client)

    # без пройденной анкеты попадаем на неё
    assert resp.headers["location"] == "/onboarding"
    assert SESSION_COOKIE in resp.cookies

    me = await api_client.get("/api/v1/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "test@example.com"
    assert body["display_name"] == "Тестовая Пользовательница"
    assert body["role"] == "user"

    identities = (
        await db_session.execute(
            select(func.count()).select_from(AuthIdentity).where(
                AuthIdentity.provider == GOOGLE_PROVIDER,
                AuthIdentity.provider_sub == "sub-test",
            )
        )
    ).scalar_one()
    user_id = await _test_user_id(db_session, "sub-test")
    sessions = (
        await db_session.execute(
            select(func.count()).select_from(UserSession).where(UserSession.user_id == user_id)
        )
    ).scalar_one()
    assert identities == 1
    assert sessions == 1

    # в базе хэш а не сырой токен, берём последнюю сессию аккаунта
    raw = api_client.cookies.get(SESSION_COOKIE)
    user_id = await _test_user_id(db_session, "sub-test")
    stored = (
        await db_session.execute(
            select(UserSession)
            .where(UserSession.user_id == user_id)
            .order_by(UserSession.created_at.desc(), UserSession.id.desc())
        )
    ).scalars().first()
    assert stored.token_hash == hash_token(raw)
    assert stored.token_hash != raw


async def test_relogin_returns_same_account(api_client, db_session, fake_google):
    fake_google()

    existing = (
        await db_session.execute(
            select(AuthIdentity).where(
                AuthIdentity.provider == GOOGLE_PROVIDER,
                AuthIdentity.provider_sub == "sub-test",
            )
        )
    ).scalar_one_or_none()

    def _count_identities():
        return (
            select(func.count())
            .select_from(AuthIdentity)
            .where(
                AuthIdentity.provider == GOOGLE_PROVIDER,
                AuthIdentity.provider_sub == "sub-test",
            )
        )

    before_identities = (await db_session.execute(_count_identities())).scalar_one()
    before_sessions = 0
    if existing:
        before_sessions = (
            await db_session.execute(
                select(func.count())
                .select_from(UserSession)
                .where(UserSession.user_id == existing.user_id)
            )
        ).scalar_one()

    await login(api_client)
    await login(api_client)

    # счёт дельтой потому что база общая между тестами
    after_identities = (await db_session.execute(_count_identities())).scalar_one()
    assert after_identities - before_identities == 0

    user_id = await _test_user_id(db_session, "sub-test")
    after_sessions = (
        await db_session.execute(
            select(func.count()).select_from(UserSession).where(UserSession.user_id == user_id)
        )
    ).scalar_one()
    assert after_sessions - before_sessions == 2


async def test_logout_revokes_session(api_client, fake_google):
    fake_google()
    await login(api_client)

    assert (await api_client.get("/api/v1/auth/me")).status_code == 200

    resp = await api_client.post("/api/v1/auth/logout")
    assert resp.status_code == 204
    assert (await api_client.get("/api/v1/auth/me")).status_code == 401

    # повторный вход создаёт новую сессию, старая отозвана
    await login(api_client)
    assert (await api_client.get("/api/v1/auth/me")).status_code == 200


async def test_unverified_email_rejected(api_client, db_session, fake_google):
    # google не подтвердил почту -> аккаунт не создаём
    fake_google(sub="sub-unverified", email="unverified@example.com", verified=False)
    resp = await api_client.get("/api/v1/auth/google/callback")

    assert resp.status_code == 400
    assert "подтвердите email" in resp.json()["detail"]

    left = (
        await db_session.execute(
            select(AuthIdentity).where(AuthIdentity.provider_sub == "sub-unverified")
        )
    ).scalar_one_or_none()
    assert left is None


async def test_logout_purges_expired_sessions(api_client, db_session, fake_google):
    fake_google()
    await login(api_client)
    user_id = await _test_user_id(db_session, "sub-test")

    db_session.add(
        UserSession(
            token_hash="e" * 64,
            user_id=user_id,
            expires_at=datetime.now(UTC) - timedelta(hours=2),
        )
    )
    await db_session.commit()

    resp = await api_client.post("/api/v1/auth/logout")
    assert resp.status_code == 204

    stale = (
        await db_session.execute(
            select(UserSession).where(UserSession.token_hash == "e" * 64)
        )
    ).scalar_one_or_none()
    assert stale is None


async def test_expired_session_rejected(api_client, db_session):
    user = User()
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        AuthIdentity(
            user_id=user.id,
            provider=GOOGLE_PROVIDER,
            provider_sub="sub-expired",
            email="expired@example.com",
        )
    )

    token = new_session_token()
    db_session.add(
        UserSession(
            token_hash=hash_token(token),
            user_id=user.id,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
    )
    await db_session.commit()

    api_client.cookies.set(SESSION_COOKIE, token)
    assert (await api_client.get("/api/v1/auth/me")).status_code == 401


async def test_admin_promotion_from_env(api_client, fake_google, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "admin_google_subs", "sub-big-boss")

    fake_google(sub="sub-big-boss", email="boss@example.com")
    await login(api_client, sub="sub-big-boss", email="boss@example.com")

    me = await api_client.get("/api/v1/auth/me")
    assert me.json()["role"] == "admin"


async def test_admin_gate_blocks_anonymous_and_plain_users(api_client, fake_google, monkeypatch):
    from app.core.config import get_settings

    # без сессии — редирект на страницу входа фронтенда (полный адрес)
    resp = await api_client.get("/admin/", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == f"{get_settings().base_url}/login"

    # обычная пользовательница — 403
    fake_google()
    await login(api_client)
    resp = await api_client.get("/admin/", follow_redirects=False)
    assert resp.status_code == 403


async def test_admin_gate_lets_staff_in(api_client, fake_google, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "admin_google_subs", "sub-staff")

    fake_google(sub="sub-staff", email="staff@example.com")
    await login(api_client, sub="sub-staff", email="staff@example.com")

    resp = await api_client.get("/admin/", follow_redirects=True)
    assert resp.status_code == 200
