from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Favorite, Story, Tag
from app.models.enums import PublicationStatus, StoryType, VerificationStatus
from app.services.stories import apply_catalog_filters

# только опубликованное можно сохранять: черновики и отклонённые не существуют для пользовательниц
PUBLISHED_FILTER = (
    Story.publication_status == PublicationStatus.PUBLISHED,
    Story.verification_status == VerificationStatus.VERIFIED,
)


async def _published_story(db: AsyncSession, slug: str) -> Story:
    story = (
        await db.execute(select(Story).where(Story.slug == slug, *PUBLISHED_FILTER))
    ).scalar_one_or_none()
    if story is None:
        raise HTTPException(status_code=404, detail="история не найдена")
    return story


async def add_favorite(db: AsyncSession, user_id, slug: str) -> None:
    story = await _published_story(db, slug)
    existing = (
        await db.execute(
            select(Favorite).where(Favorite.user_id == user_id, Favorite.story_id == story.id)
        )
    ).scalar_one_or_none()
    # повторное сохранение спокойно идемпотентно
    if existing is None:
        db.add(Favorite(user_id=user_id, story_id=story.id))


async def remove_favorite(db: AsyncSession, user_id, slug: str) -> None:
    existing = (
        await db.execute(
            select(Favorite).join(Story, Story.id == Favorite.story_id).where(
                Favorite.user_id == user_id, Story.slug == slug
            )
        )
    ).scalar_one_or_none()
    # повторное удаление не ошибка: цель достигнута
    if existing is not None:
        await db.delete(existing)


async def favorite_slugs(db: AsyncSession, user_id) -> set[str]:
    rows = (
        await db.execute(
            select(Story.slug)
            .join(Favorite, Favorite.story_id == Story.id)
            .where(Favorite.user_id == user_id, *PUBLISHED_FILTER)
        )
    ).scalars().all()
    return set(rows)


async def list_favorites(
    db: AsyncSession,
    user_id,
    *,
    q: str | None = None,
    filters: dict[str, int | None] | None = None,
    story_type: StoryType | None = None,
    sort: str = "saved",
) -> list[dict]:
    stmt = (
        select(Story)
        .join(Favorite, Favorite.story_id == Story.id)
        .where(Favorite.user_id == user_id, *PUBLISHED_FILTER)
    )
    stmt = await apply_catalog_filters(db, stmt, q=q, filters=filters, story_type=story_type)

    order = {
        # по умолчанию свежее сохранение сверху, остальное как в каталоге
        "saved": (Favorite.created_at.desc(),),
        "new": (Story.published_at.desc().nulls_last(), Story.created_at.desc()),
        "old": (Story.published_at.asc().nulls_last(), Story.created_at.asc()),
        "title": (Story.title.asc(),),
    }[sort]

    stories = (await db.execute(stmt.order_by(*order))).scalars().all()

    tag_ids = {s.country_tag_id for s in stories} | {s.profession_tag_id for s in stories}
    tag_ids.discard(None)
    names = {}
    if tag_ids:
        rows = (await db.execute(select(Tag.id, Tag.name_ru).where(Tag.id.in_(tag_ids)))).all()
        names = dict(rows)

    return [
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


async def count_favorites(db: AsyncSession, user_id) -> int:
    return (
        await db.execute(
            select(func.count()).select_from(Favorite).where(Favorite.user_id == user_id)
        )
    ).scalar_one()
