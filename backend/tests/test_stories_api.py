import pytest
from sqlalchemy import func, select

from app.models import Tag, TagGroup

pytestmark = pytest.mark.asyncio

PUBLISHED_VERIFIED = 18  # из 20 сид-историй две не проходят в каталог


async def _tag_id(db_session, group_code: str, slug: str) -> int:
    return (
        await db_session.execute(
            select(Tag.id)
            .join(TagGroup, TagGroup.id == Tag.group_id)
            .where(TagGroup.code == group_code, Tag.slug == slug)
        )
    ).scalar_one()


async def test_catalog_requires_no_auth(api_client):
    resp = await api_client.get("/api/v1/stories")
    assert resp.status_code == 200


async def test_catalog_shows_only_published_verified(api_client, db_session):
    resp = await api_client.get("/api/v1/stories", params={"limit": 50})
    body = resp.json()
    assert body["total"] == PUBLISHED_VERIFIED
    assert len(body["items"]) == PUBLISHED_VERIFIED
    slugs = {item["slug"] for item in body["items"]}
    assert "demo-nina-scientist" not in slugs  # draft
    assert "demo-lili-journalist" not in slugs  # needs_revision


async def test_catalog_search_by_name(api_client):
    resp = await api_client.get("/api/v1/stories", params={"q": "Кюри"})
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["slug"] == "demo-maria-curie"
    assert body["items"][0]["country"] == "Польша"
    assert body["items"][0]["profession"] == "Наука и исследования"


async def test_catalog_search_by_title(api_client):
    resp = await api_client.get("/api/v1/stories", params={"q": "Заголовок", "limit": 50})
    assert resp.json()["total"] == PUBLISHED_VERIFIED


async def test_catalog_search_nothing_found(api_client):
    resp = await api_client.get("/api/v1/stories", params={"q": "абракадабра"})
    body = resp.json()
    assert body["total"] == 0
    assert body["items"] == []
    assert body["pages"] == 1


async def test_catalog_filter_country(api_client, db_session):
    russia = await _tag_id(db_session, "countries", "russia")
    resp = await api_client.get("/api/v1/stories", params={"country": russia, "limit": 50})
    slugs = {i["slug"] for i in resp.json()["items"]}
    # в россии четыре опубликованные: софья, валентина, мария-разработчица, анонимный психолог
    assert slugs == {
        "demo-sofya-kovalevskaya",
        "demo-valentina-tereshkova",
        "demo-maria-developer",
        "demo-anon-psychologist",
    }
    assert all(i["country"] == "Россия" for i in resp.json()["items"])


async def test_catalog_filter_combined_country_and_type(api_client, db_session):
    russia = await _tag_id(db_session, "countries", "russia")
    resp = await api_client.get(
        "/api/v1/stories",
        params={"country": russia, "story_type": "community_story", "limit": 50},
    )
    slugs = {i["slug"] for i in resp.json()["items"]}
    assert slugs == {"demo-maria-developer", "demo-anon-psychologist"}


async def test_catalog_filter_obstacle_tag(api_client, db_session):
    gender = await _tag_id(db_session, "obstacles", "gender-stereotypes")
    resp = await api_client.get("/api/v1/stories", params={"obstacle": gender, "limit": 50})
    slugs = {i["slug"] for i in resp.json()["items"]}
    assert "demo-ada-lovelace" in slugs
    assert "demo-sofya-kovalevskaya" in slugs
    assert "demo-hedy-lamarr" in slugs


async def test_catalog_filter_theme_tag(api_client, db_session):
    science = await _tag_id(db_session, "themes", "science")
    resp = await api_client.get("/api/v1/stories", params={"theme": science, "limit": 50})
    slugs = {i["slug"] for i in resp.json()["items"]}
    assert "demo-maria-curie" in slugs
    assert "demo-nina-scientist" not in slugs  # черновик не видна даже по своей теме


async def test_catalog_filter_wrong_group_rejected(api_client, db_session):
    russia = await _tag_id(db_session, "countries", "russia")
    resp = await api_client.get("/api/v1/stories", params={"theme": russia})
    assert resp.status_code == 400
    assert "theme" in resp.json()["detail"]
    assert "themes" in resp.json()["detail"]


async def test_catalog_sortings(api_client):
    newest = await api_client.get("/api/v1/stories", params={"sort": "new", "limit": 5})
    assert newest.json()["items"][0]["slug"] == "demo-dina-lawyer"

    oldest = await api_client.get("/api/v1/stories", params={"sort": "old", "limit": 5})
    assert oldest.json()["items"][0]["slug"] == "demo-ada-lovelace"

    by_title = await api_client.get("/api/v1/stories", params={"sort": "title", "limit": 50})
    titles = [i["title"] for i in by_title.json()["items"]]
    assert titles == sorted(titles)


async def test_catalog_pagination(api_client):
    page1 = await api_client.get("/api/v1/stories", params={"limit": 5})
    body = page1.json()
    assert len(body["items"]) == 5
    assert body["page"] == 1
    assert body["pages"] == 4
    assert body["total"] == PUBLISHED_VERIFIED

    page2 = await api_client.get("/api/v1/stories", params={"limit": 5, "page": 2})
    slugs1 = {i["slug"] for i in body["items"]}
    slugs2 = {i["slug"] for i in page2.json()["items"]}
    assert slugs1 & slugs2 == set()


async def test_story_detail(api_client):
    resp = await api_client.get("/api/v1/stories/demo-ada-lovelace")
    assert resp.status_code == 200
    body = resp.json()
    assert body["woman_name"] == "Ада Лавлейс"
    assert body["story_type"] == "verified_biography"
    assert body["country"] == "Великобритания"
    assert body["age"] == "35–49"
    assert len(body["sources"]) == 3
    groups = {t["group"] for t in body["tags"]}
    assert "themes" in groups
    assert "obstacles" in groups


async def test_story_detail_hides_draft(api_client):
    resp = await api_client.get("/api/v1/stories/demo-nina-scientist")
    assert resp.status_code == 404


async def test_story_detail_unknown_slug(api_client):
    resp = await api_client.get("/api/v1/stories/no-such-story")
    assert resp.status_code == 404


async def test_placeholder_texts_mention_metadata(api_client, db_session):
    resp = await api_client.get("/api/v1/stories/demo-maria-developer")
    body = resp.json()
    # заглушка собирается из метаданных чтобы фильтры и поиск можно было тестировать
    assert "Россия" in body["short_description"]
    assert "Разработка ПО" in body["short_description"]
    assert "самозванк" in body["short_description"]  # я-формулировка сомнения
    assert "редакция" in body["full_text"]


async def test_total_counts_match_seed(api_client, db_session):
    resp = await api_client.get("/api/v1/stories", params={"limit": 50})
    seeded = (
        await db_session.execute(select(func.count()).select_from(Tag))
    ).scalar_one()
    assert seeded > 100  # словари на месте
    assert resp.json()["total"] == PUBLISHED_VERIFIED
