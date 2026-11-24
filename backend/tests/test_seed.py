from conftest import TEST_DATABASE_URL
from sqlalchemy import func, select

from app.models import Story, Tag
from app.models.enums import StoryType
from app.seed import run as seed_run


async def _counts(session):
    tags = (await session.execute(select(func.count()).select_from(Tag))).scalar_one()
    stories = (await session.execute(select(func.count()).select_from(Story))).scalar_one()
    return tags, stories


async def test_seed_is_idempotent(db_session):
    before = await _counts(db_session)

    await seed_run(TEST_DATABASE_URL)
    db_session.expire_all()

    after = await _counts(db_session)
    assert before == after


async def test_seed_removes_demo_ghosts(db_session):
    ghost = Story(
        slug="demo-ghost",
        title="призрак",
        woman_name="n",
        short_description="s",
        full_text="f",
        story_type=StoryType.VERIFIED_BIOGRAPHY,
    )
    db_session.add(ghost)
    await db_session.commit()

    await seed_run(TEST_DATABASE_URL)
    db_session.expire_all()

    leftover = (
        await db_session.execute(select(Story).where(Story.slug == "demo-ghost"))
    ).scalar_one_or_none()
    assert leftover is None


async def test_seed_story_mix(db_session):
    # считаем только демо-истории, другие тесты могли оставить свои записи
    stories = (
        await db_session.execute(
            select(Story).where(Story.slug.like("demo-%")).order_by(Story.created_at)
        )
    ).scalars().all()

    assert len(stories) == 20
    types = {story.story_type for story in stories}
    assert types == {StoryType.VERIFIED_BIOGRAPHY, StoryType.COMMUNITY_STORY}
    # есть анонимная и непубликованная
    assert any(story.is_anonymous for story in stories)
    assert any(story.publication_status.value == "draft" for story in stories)
    # у опубликованных проставлена дата
    published = [s for s in stories if s.publication_status.value == "published"]
    assert all(s.published_at is not None for s in published)
