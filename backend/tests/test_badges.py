import pytest
from sqlalchemy import select

from app.models import Story, User
from app.models.enums import UserRole

pytestmark = pytest.mark.asyncio


async def _login(api_client, fake_google, sub, email):
    fake_google(sub=sub, email=email)
    resp = await api_client.get("/api/v1/auth/google/callback")
    assert resp.status_code == 302


async def _user_id(db_session, sub):
    from app.models import AuthIdentity

    return (
        await db_session.execute(
            select(AuthIdentity.user_id).where(AuthIdentity.provider_sub == sub)
        )
    ).scalar_one()


async def _set_role(db_session, sub, role):
    user = await db_session.get(User, await _user_id(db_session, sub))
    user.role = role
    db_session.add(user)
    await db_session.commit()
    db_session.expire_all()


async def test_public_profile_and_stories(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-bdg-1", "bdg1@example.com")
    await api_client.post(
        "/api/v1/stories/submit",
        json={
            "text": "я научилась просить о помощи и хочу рассказать об этом чтобы поддержать других "
            "потому что мне самой не хватало таких историй когда я начинала",
            "consent_publication": True,
        },
    )
    uid = await _user_id(db_session, "sub-bdg-1")

    profile = (await api_client.get(f"/api/v1/u/{uid}")).json()
    # имя из google или почта — любое из них допустимо
    assert profile["display_name"] in {"bdg1@example.com", "Тестовая Пользовательница"}
    assert profile["badges"] == []
    assert profile["is_banned"] is False

    # опубликованных нет
    stories = (await api_client.get(f"/api/v1/u/{uid}/stories")).json()
    assert stories["total"] == 0

    # уборка
    story = (
        await db_session.execute(select(Story).where(Story.created_by == uid))
    ).scalar_one()
    await db_session.delete(story)
    await db_session.commit()


async def test_moderator_grants_and_revokes(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-bdg-2", "bdg2@example.com")  # авторка-жертва
    target_id = await _user_id(db_session, "sub-bdg-2")

    await _login(api_client, fake_google, "sub-bdg-3", "bdg3@example.com")  # модераторша
    await _set_role(db_session, "sub-bdg-3", UserRole.MODERATOR)

    resp = await api_client.post(
        f"/api/v1/u/{target_id}/badges", json={"badge": "author"}
    )
    assert resp.status_code == 204

    # бейдж виден в публичном профиле
    profile = (await api_client.get(f"/api/v1/u/{target_id}")).json()
    assert {b["code"] for b in profile["badges"]} == {"author"}
    assert profile["badges"][0]["label"] == "авторка"

    # роль поднялась до editor
    target = await db_session.get(User, target_id)
    db_session.expire_all()
    target = await db_session.get(User, target_id)
    assert target.role == UserRole.EDITOR

    # модераторша не может выдать создательницу
    resp = await api_client.post(f"/api/v1/u/{target_id}/badges", json={"badge": "creator"})
    assert resp.status_code == 403

    # снять бейдж
    resp = await api_client.delete(f"/api/v1/u/{target_id}/badges/author")
    assert resp.status_code == 204
    profile = (await api_client.get(f"/api/v1/u/{target_id}")).json()
    assert profile["badges"] == []


async def test_search_accounts(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-srch-1", "srch1@example.com")
    target_id = await _user_id(db_session, "sub-srch-1")

    # уникальный ник чтобы не пересечься с другими тестами
    assert (
        await api_client.patch(
            "/api/v1/profile", json={"display_name": "уникальнаямила"}
        )
    ).status_code == 200

    await _login(api_client, fake_google, "sub-srch-2", "srch2@example.com")
    await _set_role(db_session, "sub-srch-2", UserRole.MODERATOR)

    resp = await api_client.get("/api/v1/u/search", params={"q": "мила"})
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["id"] == str(target_id)
    assert items[0]["display_name"] == "уникальнаямила"

    # короткий запрос не принимается
    assert (
        await api_client.get("/api/v1/u/search", params={"q": "м"})
    ).status_code == 422

    # забаненная не находится
    assert (
        await api_client.post(f"/api/v1/u/{target_id}/ban")
    ).status_code == 204
    resp = await api_client.get("/api/v1/u/search", params={"q": "мила"})
    assert resp.json() == []


async def test_plain_user_cannot_grant(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-bdg-4", "bdg4@example.com")
    target_id = await _user_id(db_session, "sub-bdg-4")

    resp = await api_client.post(f"/api/v1/u/{target_id}/badges", json={"badge": "designer"})
    assert resp.status_code == 403


async def test_ban_flow(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-bdg-5", "bdg5@example.com")  # жертва
    target_id = await _user_id(db_session, "sub-bdg-5")
    assert (await api_client.get("/api/v1/auth/me")).status_code == 200

    await _login(api_client, fake_google, "sub-bdg-6", "bdg6@example.com")  # модераторша
    await _set_role(db_session, "sub-bdg-6", UserRole.MODERATOR)

    assert (await api_client.post(f"/api/v1/u/{target_id}/ban")).status_code == 204

    # повторный вход заблокирован сразу
    fake_google(sub="sub-bdg-5", email="bdg5@example.com")
    resp = await api_client.get("/api/v1/auth/google/callback")
    assert resp.status_code == 403
    assert "заблокирован" in resp.json()["detail"]

    # разбан
    assert (await api_client.delete(f"/api/v1/u/{target_id}/ban")).status_code == 204
    await _login(api_client, fake_google, "sub-bdg-5", "bdg5@example.com")
    assert (await api_client.get("/api/v1/auth/me")).status_code == 200


async def test_official_story_flow(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-bdg-7", "bdg7@example.com")  # авторка
    await _set_role(db_session, "sub-bdg-7", UserRole.EDITOR)
    author_id = await _user_id(db_session, "sub-bdg-7")

    resp = await api_client.post(
        "/api/v1/stories/official",
        json={
            "title": "путь первой женщины-инженера",
            "text": "официальная история должна быть подробной и опираться на источники. "
            "этот текст специально длинный чтобы пройти проверку минимум в двести символов, "
            "потому что официальные истории требуют основательности в отличие от коротких "
            "пользовательских зарисовок",
            "sources": [
                {"title": "архивная статья", "url": "https://example.com/a"},
                {"title": "интервью", "url": "https://example.com/b"},
            ],
        },
    )
    assert resp.status_code == 202
    slug = resp.json()["slug"]
    assert slug.startswith("put-pervoy-zhenschiny")

    # без источников не проходит
    bad = await api_client.post(
        "/api/v1/stories/official",
        json={
            "title": "без источников",
            "text": "текст достаточной длины для проверки валидации официальной истории которая не "
            "пройдёт потому что у неё нет ни одного источника в списке — и мы специально "
            "удлиняем этот текст сверх двухсот символов чтобы проверка дошла именно до "
            "блока источников а не срезалась на длине самой истории",
            "sources": [],
        },
    )
    assert bad.status_code == 400

    # в списке «мои истории»
    mine = (await api_client.get("/api/v1/profile/stories")).json()
    assert any(i["slug"] == slug for i in mine["items"])

    # авторка видит свою pending-страницу
    assert (await api_client.get(f"/api/v1/stories/{slug}")).status_code == 200

    # модераторша публикует
    await _set_role(db_session, "sub-bdg-7", UserRole.MODERATOR)
    pending = (await api_client.get("/api/v1/moderation/pending")).json()
    entry = next(p for p in pending if p["slug"] == slug)
    assert entry["story_type"] == "verified_biography"
    assert len(entry["sources"]) == 2

    assert (
        await api_client.post(f"/api/v1/moderation/{entry['id']}/publish")
    ).status_code == 204

    # в каталоге, с подписью авторки
    detail = (await api_client.get(f"/api/v1/stories/{slug}")).json()
    assert detail["story_type"] == "verified_biography"
    assert detail["author"]["id"] == str(author_id)
    assert len(detail["sources"]) == 2

    # в публичных историях профиля
    pub = (await api_client.get(f"/api/v1/u/{author_id}/stories")).json()
    assert any(i["slug"] == slug for i in pub["items"])

    # уборка
    story = (
        await db_session.execute(select(Story).where(Story.slug == slug))
    ).scalar_one()
    await db_session.delete(story)
    await db_session.commit()
