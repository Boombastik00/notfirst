import pytest
from sqlalchemy import select

from app.models import Tag, TagGroup, User, UserProfile

pytestmark = pytest.mark.asyncio


async def _tag_id(db_session, group_code: str, slug: str) -> int:
    return (
        await db_session.execute(
            select(Tag.id)
            .join(TagGroup, TagGroup.id == Tag.group_id)
            .where(TagGroup.code == group_code, Tag.slug == slug)
        )
    ).scalar_one()


async def _user_by_sub(db_session, sub: str) -> User:
    from app.models import AuthIdentity

    return (
        await db_session.execute(
            select(User)
            .join(AuthIdentity, AuthIdentity.user_id == User.id)
            .where(AuthIdentity.provider_sub == sub)
        )
    ).scalar_one()


async def test_onboarding_requires_auth(api_client):
    assert (await api_client.get("/api/v1/onboarding")).status_code == 401
    resp = await api_client.post("/api/v1/onboarding", json={"skip": True})
    assert resp.status_code == 401


async def test_onboarding_options(api_client, fake_google):
    fake_google(sub="sub-onb-1", email="onb1@example.com")
    await api_client.get("/api/v1/auth/google/callback")

    resp = await api_client.get("/api/v1/onboarding")
    assert resp.status_code == 200
    body = resp.json()
    assert body["already_completed"] is False
    assert len(body["options"]["age_categories"]) == 5
    assert len(body["options"]["professions"]) == 15
    assert len(body["options"]["countries"]) > 30
    assert len(body["options"]["fields"]) == 20
    assert len(body["options"]["themes"]) == 15


async def test_onboarding_full_submit(api_client, db_session, fake_google):
    fake_google(sub="sub-onb-2", email="onb2@example.com")
    await api_client.get("/api/v1/auth/google/callback")

    age = await _tag_id(db_session, "age_categories", "25-34")
    country = await _tag_id(db_session, "countries", "russia")
    profession = await _tag_id(db_session, "professions", "software-dev")
    field = await _tag_id(db_session, "fields", "it")
    theme = await _tag_id(db_session, "themes", "career-switch")
    obstacle = await _tag_id(db_session, "obstacles", "self-impostor")

    # темы при регистрации больше не спрашиваем, они остались в профиле
    resp = await api_client.post(
        "/api/v1/onboarding",
        json={
            "age_tag_id": age,
            "country_tag_id": country,
            "profession_tag_id": profession,
            "current_field_tag_id": field,
            "interest_tag_ids": [theme],
        },
    )
    assert resp.status_code == 400

    resp = await api_client.post(
        "/api/v1/onboarding",
        json={
            "age_tag_id": age,
            "country_tag_id": country,
            "profession_tag_id": profession,
            "interest_tag_ids": [obstacle],
        },
    )
    # сомнение в интересы не проходит
    assert resp.status_code == 400
    assert "интересах" in resp.json()["detail"]

    resp = await api_client.post(
        "/api/v1/onboarding",
        json={
            "age_tag_id": age,
            "country_tag_id": country,
            "profession_tag_id": profession,
            "interest_tag_ids": [field],
        },
    )
    assert resp.status_code == 204

    db_session.expire_all()
    user = await _user_by_sub(db_session, "sub-onb-2")
    profile = (
        await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
    ).scalar_one()
    assert profile.age_tag_id == age
    assert profile.country_tag_id == country
    assert profile.profession_tag_id == profession
    assert user.onboarding_completed is True

    me = await api_client.get("/api/v1/auth/me")
    assert me.json()["onboarding_completed"] is True

    # следующий вход ведёт сразу на главную
    await api_client.get("/api/v1/auth/google/callback")
    assert api_client.cookies is not None


async def test_onboarding_age_required_without_skip(api_client, fake_google):
    fake_google(sub="sub-onb-3", email="onb3@example.com")
    await api_client.get("/api/v1/auth/google/callback")

    resp = await api_client.post("/api/v1/onboarding", json={})
    assert resp.status_code == 400
    assert "возрастную категорию" in resp.json()["detail"]


async def test_onboarding_wrong_group_rejected(api_client, db_session, fake_google):
    fake_google(sub="sub-onb-4", email="onb4@example.com")
    await api_client.get("/api/v1/auth/google/callback")

    country = await _tag_id(db_session, "countries", "russia")
    resp = await api_client.post("/api/v1/onboarding", json={"age_tag_id": country})
    assert resp.status_code == 400


async def test_onboarding_skip(api_client, db_session, fake_google):
    fake_google(sub="sub-onb-5", email="onb5@example.com")
    await api_client.get("/api/v1/auth/google/callback")

    resp = await api_client.post("/api/v1/onboarding", json={"skip": True})
    assert resp.status_code == 204

    db_session.expire_all()
    user = await _user_by_sub(db_session, "sub-onb-5")
    profile = (
        await db_session.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
    ).scalar_one()
    assert profile.age_tag_id is None
    assert user.onboarding_completed is True
