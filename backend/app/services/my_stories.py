from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Story, Tag

# статусы для карточек «мои истории»: авторка видит и неопубликованное
STATUS_LABELS = {
    ("pending", "draft"): "на модерации",
    ("pending", "published"): "на модерации",
    ("verified", "published"): "опубликована",
    ("verified", "draft"): "готова к публикации",
    ("rejected", "draft"): "отклонена",
    ("needs_revision", "published"): "на доработке",
    ("needs_revision", "draft"): "на доработке",
    ("archived", "published"): "в архиве",
    ("archived", "draft"): "в архиве",
}


async def list_my_stories(db: AsyncSession, user_id) -> list[dict]:
    stories = (
        (
            await db.execute(
                select(Story)
                .where(Story.created_by == user_id)
                .order_by(Story.created_at.desc())
            )
        )
        .scalars()
        .all()
    )

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
            "short_description": s.short_description,
            "story_type": s.story_type.value,
            "verification_status": s.verification_status.value,
            "publication_status": s.publication_status.value,
            "created_at": s.created_at,
            "country": names.get(s.country_tag_id),
            "profession": names.get(s.profession_tag_id),
        }
        for s in stories
    ]
