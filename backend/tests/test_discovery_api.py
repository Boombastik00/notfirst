import pytest
from sqlalchemy import select

from app.models import Story, Tag, TagGroup, User

pytestmark = pytest.mark.asyncio


async def _login(api_client, fake_google, sub, email):
    fake_google(sub=sub, email=email)
    resp = await api_client.get("/api/v1/auth/google/callback")
    assert resp.status_code == 302


async def _tag_id(db_session, group_code: str, slug: str) -> int:
    return (
        await db_session.execute(
            select(Tag.id)
            .join(TagGroup, TagGroup.id == Tag.group_id)
            .where(TagGroup.code == group_code, Tag.slug == slug)
        )
    ).scalar_one()


async def test_story_of_the_day_public_and_stable(api_client, db_session):
    resp = await api_client.get("/api/v1/stories/daily")
    assert resp.status_code == 200
    slug_first = resp.json()["story"]["slug"]
    assert slug_first.startswith("demo-")

    # повторный запрос в тот же день даёт ту же историю
    resp2 = await api_client.get("/api/v1/stories/daily")
    assert resp2.json()["story"]["slug"] == slug_first


async def test_random_requires_auth(api_client):
    assert (await api_client.get("/api/v1/stories/random")).status_code == 401


async def test_random_respects_profile(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-disc-1", "disc1@example.com")
    russia = await _tag_id(db_session, "countries", "russia")

    from app.models import AuthIdentity, UserProfile

    uid = (
        await db_session.execute(
            select(AuthIdentity.user_id).where(AuthIdentity.provider_sub == "sub-disc-1")
        )
    ).scalar_one()
    profile = await db_session.get(UserProfile, uid)
    profile.country_tag_id = russia
    db_session.add(profile)
    await db_session.commit()

    for _ in range(3):
        resp = await api_client.get("/api/v1/stories/random")
        assert resp.status_code == 200
        assert resp.json()["story"]["country"] == "Россия"


async def test_recommendation_by_obstacle(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-disc-2", "disc2@example.com")
    impostor = await _tag_id(db_session, "obstacles", "self-impostor")
    it_field = await _tag_id(db_session, "fields", "it")

    resp = await api_client.get(
        "/api/v1/recommendations", params={"obstacle": impostor, "field": it_field}
    )
    assert resp.status_code == 200
    feed = resp.json()["feed"]
    # у анонимного психолога то же сомнение, но сфера it добивает в пользу марии
    assert feed[0]["story"]["slug"] == "demo-maria-developer"
    assert feed[0]["random"] is False
    dims = [r["dimension"] for r in feed[0]["match_reasons"]]
    assert "obstacle" in dims
    assert "field" in dims
    # дальше по убыванию очков
    assert len(feed) > 1
    assert feed[1]["story"]["slug"] == "demo-anon-psychologist"


async def test_recommendation_multiple_obstacles(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-disc-7", "disc7@example.com")
    impostor = await _tag_id(db_session, "obstacles", "self-impostor")
    gender_env = await _tag_id(db_session, "obstacles", "gender-env")

    resp = await api_client.get(
        "/api/v1/recommendations", params=[("obstacle", impostor), ("obstacle", gender_env)]
    )
    assert resp.status_code == 200
    feed = resp.json()["feed"]
    # у марии оба сомнения — она и должна выиграть
    assert feed[0]["story"]["slug"] == "demo-maria-developer"
    obstacle_reasons = [r for r in feed[0]["match_reasons"] if r["dimension"] == "obstacle"]
    assert len(obstacle_reasons) == 2


async def test_recommendation_no_match_falls_back_random(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-disc-3", "disc3@example.com")
    # пустой профиль и никаких ответов — просто случайная история без причин
    resp = await api_client.get("/api/v1/recommendations")
    assert resp.status_code == 200
    feed = resp.json()["feed"]
    assert len(feed) > 0
    assert feed[0]["story"] is not None
    assert feed[0]["match_reasons"] == []
    assert feed[0]["random"] is True


async def test_recommendation_requires_auth(api_client):
    assert (await api_client.get("/api/v1/recommendations")).status_code == 401


async def test_submit_and_moderation_publish(api_client, db_session, fake_google, monkeypatch):
    await _login(api_client, fake_google, "sub-disc-4", "disc4@example.com")
    field = await _tag_id(db_session, "fields", "it")

    resp = await api_client.post(
        "/api/v1/stories/submit",
        json={
            "text": "я смогла перейти в разработку после тридцати и хочу рассказать как это было "
            "потому что мне самой не хватало таких историй когда я начинала",
            "title": "мой путь",
            "field_tag_id": field,
            "consent_publication": True,
        },
    )
    assert resp.status_code == 202
    slug = resp.json()["slug"]

    # чужой и гость получают 404 на неопубликованную
    resp = await api_client.get(f"/api/v1/stories/{slug}")
    assert resp.status_code == 200  # авторка видит свою pending-историю

    # обычной пользовательнице модерация недоступна
    assert (await api_client.get("/api/v1/moderation/pending")).status_code == 403

    # повышаем до редакторки
    from app.models import AuthIdentity
    from app.models.enums import UserRole

    uid = (
        await db_session.execute(
            select(AuthIdentity.user_id).where(AuthIdentity.provider_sub == "sub-disc-4")
        )
    ).scalar_one()
    user = await db_session.get(User, uid)
    user.role = UserRole.EDITOR
    db_session.add(user)
    await db_session.commit()
    db_session.expire_all()

    pending = (await api_client.get("/api/v1/moderation/pending")).json()
    ours = [p for p in pending if p["slug"] == slug]
    assert len(ours) == 1
    story_id = ours[0]["id"]

    assert (
        await api_client.post(f"/api/v1/moderation/{story_id}/publish")
    ).status_code == 204

    # теперь история публична
    detail = await api_client.get(f"/api/v1/stories/{slug}")
    assert detail.status_code == 200
    assert detail.json()["story_type"] == "community_story"

    # убираем за собой: каталог ниже по алфавиту ждёт ровно 18 демо-историй
    story = (
        await db_session.execute(select(Story).where(Story.slug == slug))
    ).scalar_one()
    await db_session.delete(story)
    await db_session.commit()


async def test_submit_rejection_sets_notice(api_client, db_session, fake_google):
    await _login(api_client, fake_google, "sub-disc-5", "disc5@example.com")

    resp = await api_client.post(
        "/api/v1/stories/submit",
        json={
            "text": "коротко о моей победе над страхом публичных выступлений на конференции",
            "consent_publication": True,
        },
    )
    assert resp.status_code == 202
    slug = resp.json()["slug"]

    from app.models import AuthIdentity
    from app.models.enums import UserRole

    uid = (
        await db_session.execute(
            select(AuthIdentity.user_id).where(AuthIdentity.provider_sub == "sub-disc-5")
        )
    ).scalar_one()
    user = await db_session.get(User, uid)
    user.role = UserRole.MODERATOR
    db_session.add(user)
    await db_session.commit()
    db_session.expire_all()

    pending = (await api_client.get("/api/v1/moderation/pending")).json()
    story_id = next(p for p in pending if p["slug"] == slug)["id"]

    assert (await api_client.post(f"/api/v1/moderation/{story_id}/reject")).status_code == 204

    # история исчезла
    assert (await api_client.get(f"/api/v1/stories/{slug}")).status_code == 404

    # у авторки появился одноразовый флаг
    db_session.expire_all()
    me = await api_client.get("/api/v1/auth/me")
    assert me.json()["has_rejection_notice"] is True

    # acknowledge снимает флаг навсегда
    assert (await api_client.post("/api/v1/profile/acknowledge-rejection")).status_code == 204
    me = await api_client.get("/api/v1/auth/me")
    assert me.json()["has_rejection_notice"] is False


async def test_submit_validates_text_and_tags(api_client, fake_google):
    await _login(api_client, fake_google, "sub-disc-6", "disc6@example.com")

    too_short = await api_client.post("/api/v1/stories/submit", json={"text": "мало"})
    assert too_short.status_code == 400

    resp = await api_client.post(
        "/api/v1/stories/submit",
        json={
            "text": "достаточно длинный текст истории чтобы пройти проверку длины",
            "profession_tag_id": 999999,
            "consent_publication": True,
        },
    )
    assert resp.status_code == 400
