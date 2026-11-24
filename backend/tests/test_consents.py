import pytest
from sqlalchemy import select

from app.models import Tag, TagGroup, UserConsent

pytestmark = pytest.mark.asyncio


async def _login(api_client, fake_google, sub, email, consent=False):
    fake_google(sub=sub, email=email)
    url = "/api/v1/auth/google/callback"
    if consent:
        # имитируем что экран согласий был пройден: сессия помнит версию
        resp = await api_client.get("/api/v1/auth/google/start?consent=2026-11-24")
        # start делает редирект на google, для теста важна только сессионная cookie
        assert resp.status_code in (302, 503)
        if resp.status_code == 302:
            return (await api_client.get(url)).status_code
    return (await api_client.get(url)).status_code


async def _consent_kinds(db_session, sub):
    from app.models import AuthIdentity

    uid = (
        await db_session.execute(
            select(AuthIdentity.user_id).where(AuthIdentity.provider_sub == sub)
        )
    ).scalar_one()
    rows = (
        await db_session.execute(
            select(UserConsent.kind).where(UserConsent.user_id == uid)
        )
    ).scalars().all()
    return set(rows)


async def test_no_consent_recorded_without_screen(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-cons-1", "cons1@example.com")
    assert "terms" not in await _consent_kinds(db_session, "sub-cons-1")


async def test_terms_and_pd_consents_recorded(api_client, db_session, fake_google, monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setattr(get_settings(), "google_client_id", "test-id")
    await _login(api_client, fake_google, "sub-cons-2", "cons2@example.com", consent=True)
    kinds = await _consent_kinds(db_session, "sub-cons-2")
    assert {"terms", "pd_processing"} <= kinds


async def test_under18_requires_parent_consent(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-cons-3", "cons3@example.com")
    under18 = (
        await db_session.execute(
            select(Tag.id)
            .join(TagGroup, TagGroup.id == Tag.group_id)
            .where(TagGroup.code == "age_categories", Tag.slug == "under-18")
        )
    ).scalar_one()

    resp = await api_client.post("/api/v1/onboarding", json={"age_tag_id": under18})
    assert resp.status_code == 400
    assert "законного представителя" in resp.json()["detail"]

    resp = await api_client.post(
        "/api/v1/onboarding", json={"age_tag_id": under18, "parent_confirmed": True}
    )
    assert resp.status_code == 204
    assert "parental" in await _consent_kinds(db_session, "sub-cons-3")


async def test_submit_requires_publication_consent(api_client, fake_google):
    await _login(api_client, fake_google, "sub-cons-4", "cons4@example.com")
    body = {
        "text": "достаточно длинный текст для проверки согласия на публикацию истории",
    }
    resp = await api_client.post("/api/v1/stories/submit", json=body)
    assert resp.status_code == 400
    assert "распространение" in resp.json()["detail"]
