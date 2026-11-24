import pytest
from sqlalchemy import select

from app.models import Favorite, Tag, TagGroup

pytestmark = pytest.mark.asyncio


async def _tag_id(db_session, group_code: str, slug: str) -> int:
    return (
        await db_session.execute(
            select(Tag.id)
            .join(TagGroup, TagGroup.id == Tag.group_id)
            .where(TagGroup.code == group_code, Tag.slug == slug)
        )
    ).scalar_one()


async def _login(api_client, fake_google, sub, email):
    fake_google(sub=sub, email=email)
    resp = await api_client.get("/api/v1/auth/google/callback")
    assert resp.status_code == 302


async def _user_id_by_sub(db_session, sub):
    from app.models import AuthIdentity, User

    return (
        await db_session.execute(
            select(User.id)
            .join(AuthIdentity, AuthIdentity.user_id == User.id)
            .where(AuthIdentity.provider_sub == sub)
        )
    ).scalar_one()


async def test_favorites_require_auth(api_client):
    assert (await api_client.get("/api/v1/favorites")).status_code == 401
    resp = await api_client.put("/api/v1/favorites/demo-ada-lovelace")
    assert resp.status_code == 401
    resp = await api_client.delete("/api/v1/favorites/demo-ada-lovelace")
    assert resp.status_code == 401


async def test_add_list_remove_cycle(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-fav-1", "fav1@example.com")

    resp = await api_client.put("/api/v1/favorites/demo-ada-lovelace")
    assert resp.status_code == 204
    # идемпотентность: второй put не ошибка и не дубль
    assert (await api_client.put("/api/v1/favorites/demo-ada-lovelace")).status_code == 204

    resp = await api_client.get("/api/v1/favorites")
    body = resp.json()
    assert body["total"] == 1
    card = body["items"][0]
    assert card["slug"] == "demo-ada-lovelace"
    assert card["woman_name"] == "Ада Лавлейс"
    assert card["country"] == "Великобритания"

    assert (await api_client.delete("/api/v1/favorites/demo-ada-lovelace")).status_code == 204
    # повторное удаление тоже не ошибка
    assert (await api_client.delete("/api/v1/favorites/demo-ada-lovelace")).status_code == 204
    assert (await api_client.get("/api/v1/favorites")).json()["total"] == 0


async def test_cannot_favorite_draft_or_unknown(api_client, fake_google):
    await _login(api_client, fake_google, "sub-fav-2", "fav2@example.com")

    # черновик существует но не опубликован
    assert (await api_client.put("/api/v1/favorites/demo-nina-scientist")).status_code == 404
    # несуществующий слаг
    assert (await api_client.put("/api/v1/favorites/net-takoy")).status_code == 404


async def test_favorites_isolated_between_users(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-fav-3", "fav3@example.com")
    await api_client.put("/api/v1/favorites/demo-maria-curie")

    await _login(api_client, fake_google, "sub-fav-4", "fav4@example.com")
    body = (await api_client.get("/api/v1/favorites")).json()
    assert body["total"] == 0

    user3 = await _user_id_by_sub(db_session, "sub-fav-3")
    rows = (
        await db_session.execute(select(Favorite).where(Favorite.user_id == user3))
    ).scalars().all()
    assert len(rows) == 1


async def test_favorites_survive_relogin(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-fav-5", "fav5@example.com")
    await api_client.put("/api/v1/favorites/demo-frida-kahlo")

    # новый вход = новая сессия, но избранное привязано к аккаунту
    await _login(api_client, fake_google, "sub-fav-5", "fav5@example.com")
    body = (await api_client.get("/api/v1/favorites")).json()
    assert body["total"] == 1
    assert body["items"][0]["slug"] == "demo-frida-kahlo"


async def test_favorites_filters(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-fav-6", "fav6@example.com")
    await api_client.put("/api/v1/favorites/demo-ada-lovelace")
    await api_client.put("/api/v1/favorites/demo-maria-developer")

    # поиск по имени героини
    body = (await api_client.get("/api/v1/favorites", params={"q": "Ада"})).json()
    assert [i["slug"] for i in body["items"]] == ["demo-ada-lovelace"]

    # фильтр по стране
    russia = await _tag_id(db_session, "countries", "russia")
    body = (await api_client.get("/api/v1/favorites", params={"country": russia})).json()
    assert [i["slug"] for i in body["items"]] == ["demo-maria-developer"]

    # фильтр по теме: у ада есть science
    science = await _tag_id(db_session, "themes", "science")
    body = (await api_client.get("/api/v1/favorites", params={"theme": science})).json()
    assert [i["slug"] for i in body["items"]] == ["demo-ada-lovelace"]

    # тип истории
    body = (
        await api_client.get("/api/v1/favorites", params={"story_type": "community_story"})
    ).json()
    assert [i["slug"] for i in body["items"]] == ["demo-maria-developer"]

    # ничего не подошло
    body = (await api_client.get("/api/v1/favorites", params={"q": "абракадабра"})).json()
    assert body["total"] == 0

    # не та группа тега -> 400 как в каталоге
    resp = await api_client.get("/api/v1/favorites", params={"theme": russia})
    assert resp.status_code == 400


async def test_favorites_sort_title(api_client, fake_google):
    await _login(api_client, fake_google, "sub-fav-7", "fav7@example.com")
    await api_client.put("/api/v1/favorites/demo-maria-developer")
    await api_client.put("/api/v1/favorites/demo-ada-lovelace")

    body = (await api_client.get("/api/v1/favorites", params={"sort": "title"})).json()
    titles = [i["title"] for i in body["items"]]
    assert titles == sorted(titles)
