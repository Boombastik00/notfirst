from sqlalchemy import select

from app.models import TagGroup
from app.services.tags import get_group_codes, list_tag_groups, list_tags


async def test_all_groups_seeded(db_session):
    groups = await list_tag_groups(db_session)

    codes = {group.code for group in groups}
    assert codes == {
        "age_categories",
        "countries",
        "professions",
        "fields",
        "obstacles",
        "life_circumstances",
        "achievements",
        "themes",
    }


async def test_obstacles_have_categories_and_subtags(db_session):
    tags = await list_tags(db_session, "obstacles")

    categories = [tag for tag in tags if tag.parent_id is None]
    subtags = [tag for tag in tags if tag.parent_id is not None]
    # 10 категорий из требований и заметное число подтегов
    assert len(categories) == 10
    assert len(subtags) >= 25


async def test_professions_seeded_15(db_session):
    tags = await list_tags(db_session, "professions")
    assert len(tags) == 15


async def test_age_categories_match_agreed_five(db_session):
    group = (
        await db_session.execute(select(TagGroup).where(TagGroup.code == "age_categories"))
    ).scalar_one()
    tags = await list_tags(db_session, "age_categories")
    assert [tag.slug for tag in tags] == ["under-18", "18-24", "25-34", "35-49", "50-plus"]
    assert all(tag.group_id == group.id for tag in tags)


async def test_group_codes_helper(db_session):
    codes = await get_group_codes(db_session)
    assert "obstacles" in codes
    assert "no-such-group" not in codes
