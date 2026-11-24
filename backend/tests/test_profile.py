import pytest
from sqlalchemy import select

from app.models import AuthIdentity, Tag, TagGroup, User

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


async def test_profile_requires_auth(api_client):
    assert (await api_client.get("/api/v1/profile")).status_code == 401


async def test_profile_get_and_patch(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-prof-1", "prof1@example.com")

    age = await _tag_id(db_session, "age_categories", "18-24")
    resp = await api_client.get("/api/v1/profile")
    assert resp.status_code == 200
    assert resp.json()["email"] == "prof1@example.com"
    assert resp.json()["age"] is None

    resp = await api_client.patch(
        "/api/v1/profile",
        json={"display_name": "Пользовательница Тестовая", "age_tag_id": age},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == "Пользовательница Тестовая"
    assert body["age"]["slug"] == "18-24"


async def test_profile_patch_clears_with_null(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-prof-2", "prof2@example.com")

    age = await _tag_id(db_session, "age_categories", "25-34")
    await api_client.patch("/api/v1/profile", json={"age_tag_id": age})
    resp = await api_client.patch("/api/v1/profile", json={"age_tag_id": None})
    assert resp.status_code == 200
    assert resp.json()["age"] is None


async def test_profile_patch_validates_group(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-prof-3", "prof3@example.com")

    country = await _tag_id(db_session, "countries", "russia")
    resp = await api_client.patch("/api/v1/profile", json={"age_tag_id": country})
    assert resp.status_code == 400


async def test_interests_replace_and_validation(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-prof-4", "prof4@example.com")

    theme1 = await _tag_id(db_session, "themes", "science")
    theme2 = await _tag_id(db_session, "themes", "leadership")
    field = await _tag_id(db_session, "fields", "media")
    obstacle = await _tag_id(db_session, "obstacles", "gender-env")

    resp = await api_client.put("/api/v1/profile/tags", json={"tag_ids": [theme1, field]})
    assert resp.status_code == 200
    slugs = sorted(t["slug"] for t in resp.json()["interests"])
    assert slugs == ["media", "science"]

    # замена а не накопление
    resp = await api_client.put("/api/v1/profile/tags", json={"tag_ids": [theme2]})
    assert resp.status_code == 200
    assert [t["slug"] for t in resp.json()["interests"]] == ["leadership"]

    # сомнение как интерес не проходит
    resp = await api_client.put("/api/v1/profile/tags", json={"tag_ids": [obstacle]})
    assert resp.status_code == 400


async def test_account_delete_full(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-prof-5", "prof5@example.com")

    age = await _tag_id(db_session, "age_categories", "35-49")
    await api_client.patch("/api/v1/profile", json={"age_tag_id": age})

    assert (await api_client.get("/api/v1/auth/me")).status_code == 200

    resp = await api_client.post("/api/v1/account/delete")
    assert resp.status_code == 204

    # сессия умерла вместе с аккаунтом
    assert (await api_client.get("/api/v1/auth/me")).status_code == 401

    db_session.expire_all()
    left_identity = (
        await db_session.execute(
            select(AuthIdentity).where(AuthIdentity.provider_sub == "sub-prof-5")
        )
    ).scalar_one_or_none()
    left_user = (
        await db_session.execute(
            select(User).where(
                User.id.in_(
                    select(AuthIdentity.user_id).where(
                        AuthIdentity.provider_sub == "sub-prof-5"
                    )
                )
            )
        )
    ).scalar_one_or_none()
    assert left_identity is None
    assert left_user is None
