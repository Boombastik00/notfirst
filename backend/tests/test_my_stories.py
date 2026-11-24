import pytest
from sqlalchemy import select

from app.models import Story

pytestmark = pytest.mark.asyncio


async def _login(api_client, fake_google, sub, email):
    fake_google(sub=sub, email=email)
    resp = await api_client.get("/api/v1/auth/google/callback")
    assert resp.status_code == 302


async def test_my_stories_requires_auth(api_client):
    assert (await api_client.get("/api/v1/profile/stories")).status_code == 401


async def test_my_stories_full_cycle(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-mine-1", "mine1@example.com")

    # пока пусто
    body = (await api_client.get("/api/v1/profile/stories")).json()
    assert body["total"] == 0

    # отправляем историю (останется на модерации)
    submit = await api_client.post(
        "/api/v1/stories/submit",
        json={
            "text": "я решилась сменить профессию после тридцати и хочу рассказать как справлялась со страхом "
            "потому что мне самой не хватало таких историй когда я начинала",
            "consent_publication": True,
        },
    )
    assert submit.status_code == 202
    slug = submit.json()["slug"]

    body = (await api_client.get("/api/v1/profile/stories")).json()
    assert body["total"] == 1
    card = body["items"][0]
    assert card["slug"] == slug
    assert card["verification_status"] == "pending"

    # авторка открывает свою неопубликованную историю по прямой ссылке
    detail = await api_client.get(f"/api/v1/stories/{slug}")
    assert detail.status_code == 200
    assert detail.json()["slug"] == slug

    # а чужой и гость получают 404
    await _login(api_client, fake_google, "sub-mine-2", "mine2@example.com")
    assert (await api_client.get(f"/api/v1/stories/{slug}")).status_code == 404

    # уборка за собой
    story = (
        await db_session.execute(select(Story).where(Story.slug == slug))
    ).scalar_one()
    await db_session.delete(story)
    await db_session.commit()


async def test_my_stories_not_leak_others(api_client, fake_google):
    await _login(api_client, fake_google, "sub-mine-3", "mine3@example.com")
    body = (await api_client.get("/api/v1/profile/stories")).json()
    # демо-истории сид-контента созданы не этой пользовательницей
    assert all(not i["slug"].startswith("demo-") for i in body["items"])
