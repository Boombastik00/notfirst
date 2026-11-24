from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Story, StorySource, StoryTag, Tag
from app.models.enums import PublicationStatus, StoryType, VerificationStatus
from app.models.tag import TagGroup

# какой фильтр каким словарём распоряжается
FILTER_GROUPS = {
    "country": "countries",
    "profession": "professions",
    "field": "fields",
    "obstacle": "obstacles",
    "theme": "themes",
}

SORTINGS = ("new", "old", "title")


async def _validate_filter_tags(db: AsyncSession, filters: dict[str, int | None]) -> dict[str, int]:
    ids = {value for value in filters.values() if value}
    if not ids:
        return {}

    rows = (
        await db.execute(
            select(Tag.id, TagGroup.code).join(TagGroup, TagGroup.id == Tag.group_id).where(Tag.id.in_(ids))
        )
    ).all()
    id_to_group = dict(rows)

    for name, tag_id in filters.items():
        if tag_id is None:
            continue
        if id_to_group.get(tag_id) != FILTER_GROUPS[name]:
            raise HTTPException(
                status_code=400,
                detail=f"фильтр {name} ожидает тег из группы {FILTER_GROUPS[name]}",
            )
    return {name: value for name, value in filters.items() if value}


def sanitize_query(q: str) -> str:
    # из поиска уходят управляющие символы: postgres не принимает \x00 в строках,
    # а прочий мусор вроде \r\n только шумит
    return "".join(ch for ch in q.strip() if ch >= " ")


async def apply_catalog_filters(
    db: AsyncSession,
    stmt,
    *,
    q: str | None = None,
    filters: dict[str, int | None] | None = None,
    story_type: StoryType | None = None,
):
    # общий хелпер фильтрации: им пользуются и каталог и избранное
    if q:
        pattern = f"%{sanitize_query(q)}%"
        if pattern != "%%":
            stmt = stmt.where(
                or_(
                    Story.title.ilike(pattern),
                    Story.woman_name.ilike(pattern),
                    Story.short_description.ilike(pattern),
                )
            )

    clean_filters = await _validate_filter_tags(db, filters or {})
    if clean_filters.get("country"):
        stmt = stmt.where(Story.country_tag_id == clean_filters["country"])
    if clean_filters.get("profession"):
        stmt = stmt.where(Story.profession_tag_id == clean_filters["profession"])

    # m2m-теги: тема, препятствие, сфера
    for name in ("field", "obstacle", "theme"):
        tag_id = clean_filters.get(name)
        if tag_id:
            stmt = stmt.where(
                Story.id.in_(select(StoryTag.story_id).where(StoryTag.tag_id == tag_id))
            )

    if story_type is not None:
        stmt = stmt.where(Story.story_type == story_type)
    return stmt


async def list_stories(
    db: AsyncSession,
    *,
    q: str | None = None,
    filters: dict[str, int | None] | None = None,
    story_type: StoryType | None = None,
    sort: str = "new",
    page: int = 1,
    limit: int = 20,
) -> dict:
    # каталог показывает только опубликованное и проверенное
    stmt = select(Story).where(
        Story.publication_status == PublicationStatus.PUBLISHED,
        Story.verification_status == VerificationStatus.VERIFIED,
    )
    stmt = await apply_catalog_filters(db, stmt, q=q, filters=filters, story_type=story_type)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    pages = max(1, -(-total // limit))

    order = {
        "new": (Story.published_at.desc().nulls_last(), Story.created_at.desc()),
        "old": (Story.published_at.asc().nulls_last(), Story.created_at.asc()),
        "title": (Story.title.asc(),),
    }[sort]

    stories = (
        (
            await db.execute(
                stmt.order_by(*order).offset((page - 1) * limit).limit(limit)
            )
        )
        .scalars()
        .all()
    )

    # имена страны и профессии для карточек одним запросом
    tag_ids = {s.country_tag_id for s in stories} | {s.profession_tag_id for s in stories}
    tag_ids.discard(None)
    names = {}
    if tag_ids:
        rows = (await db.execute(select(Tag.id, Tag.name_ru).where(Tag.id.in_(tag_ids)))).all()
        names = dict(rows)

    items = [
        {
            "slug": s.slug,
            "title": s.title,
            "woman_name": s.woman_name,
            "short_description": s.short_description,
            "story_type": s.story_type.value,
            "is_anonymous": s.is_anonymous,
            "published_at": s.published_at,
            "country": names.get(s.country_tag_id),
            "profession": names.get(s.profession_tag_id),
        }
        for s in stories
    ]
    return {"items": items, "total": total, "page": page, "pages": pages, "limit": limit}


async def get_own_story(db: AsyncSession, slug: str, user_id) -> dict | None:
    # авторка может открыть свою историю до публикации, статусы не важны
    story = (
        await db.execute(
            select(Story).where(Story.slug == slug, Story.created_by == user_id)
        )
    ).scalar_one_or_none()
    if story is None:
        return None
    return await _detail_dict(db, story)


async def get_published_story(db: AsyncSession, slug: str) -> dict | None:
    story = (
        await db.execute(
            select(Story).where(
                Story.slug == slug,
                Story.publication_status == PublicationStatus.PUBLISHED,
                Story.verification_status == VerificationStatus.VERIFIED,
            )
        )
    ).scalar_one_or_none()
    if story is None:
        return None
    return await _detail_dict(db, story)


async def _detail_dict(db: AsyncSession, story: Story) -> dict:
    tag_rows = (
        await db.execute(
            select(Tag.name_ru, TagGroup.code)
            .join(StoryTag, StoryTag.tag_id == Tag.id)
            .join(TagGroup, TagGroup.id == Tag.group_id)
            .where(StoryTag.story_id == story.id)
            .order_by(Tag.sort_order)
        )
    ).all()

    sources = (
        (
            await db.execute(
                select(StorySource).where(StorySource.story_id == story.id).order_by(StorySource.id)
            )
        )
        .scalars()
        .all()
    )

    tag_names = {}
    if {story.country_tag_id, story.profession_tag_id, story.age_tag_id} - {None}:
        ids = {story.country_tag_id, story.profession_tag_id, story.age_tag_id}
        ids.discard(None)
        rows = (await db.execute(select(Tag.id, Tag.name_ru).where(Tag.id.in_(ids)))).all()
        tag_names = dict(rows)

    # подпись авторки для официальных историй: имя и ссылка на профиль
    author = None
    if story.created_by is not None:
        from app.models import UserProfile as Profile

        profile = await db.get(Profile, story.created_by)
        display = (profile.display_name if profile else None) or story.woman_name
        author = {"id": str(story.created_by), "display_name": display}

    return {
        "slug": story.slug,
        "title": story.title,
        "woman_name": story.woman_name,
        "short_description": story.short_description,
        "full_text": story.full_text,
        "story_type": story.story_type.value,
        "is_anonymous": story.is_anonymous,
        "published_at": story.published_at,
        "country": tag_names.get(story.country_tag_id),
        "profession": tag_names.get(story.profession_tag_id),
        "age": tag_names.get(story.age_tag_id),
        "tags": [{"name": name, "group": code} for name, code in tag_rows],
        "sources": [
            {"title": s.title, "url": s.url, "source_type": s.source_type.value} for s in sources
        ],
        "author": author,
    }
