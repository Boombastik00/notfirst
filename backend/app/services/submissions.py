from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Story, StoryTag, Tag, TagGroup, User, UserProfile
from app.models.enums import (
    PublicationStatus,
    StoryType,
    VerificationStatus,
)

# пользовательская история: пока это черновик на модерации
SUBMIT_STATUS = (VerificationStatus.PENDING, PublicationStatus.DRAFT)


async def submit_story(
    db: AsyncSession,
    user: User,
    *,
    text: str,
    title: str | None = None,
    field_tag_id: int | None = None,
    profession_tag_id: int | None = None,
    obstacle_tag_id: int | None = None,
    consent_publication: bool = False,
) -> Story:
    text = text.strip()
    if not consent_publication:
        raise HTTPException(
            status_code=400,
            detail="для публикации нужно согласие на распространение сведений из истории",
        )
    if len(text) < 50:
        raise HTTPException(status_code=400, detail="расскажите чуть подробнее, хотя бы пару предложений")
    if len(text) > 15000:
        raise HTTPException(status_code=400, detail="история получилась слишком длинной")

    async def _checked(tag_id: int | None, group: str) -> int | None:
        if tag_id is None:
            return None
        row = (
            await db.execute(
                select(Tag.id)
                .join(TagGroup, TagGroup.id == Tag.group_id)
                .where(Tag.id == tag_id, TagGroup.code == group)
            )
        ).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=400, detail=f"тег не из группы {group}")
        return row

    field_tag_id = await _checked(field_tag_id, "fields")
    profession_tag_id = await _checked(profession_tag_id, "professions")
    obstacle_tag_id = await _checked(obstacle_tag_id, "obstacles")

    story = Story(
        slug=await _unique_slug(db),
        title=title.strip() if title and title.strip() else "история без названия",
        woman_name=await _display_name(db, user),
        short_description=text[:200].rsplit(" ", 1)[0] + "…",
        full_text=text,
        story_type=StoryType.COMMUNITY_STORY,
        verification_status=SUBMIT_STATUS[0],
        publication_status=SUBMIT_STATUS[1],
        profession_tag_id=profession_tag_id,
        is_anonymous=False,
        created_by=user.id,
    )
    db.add(story)
    await db.flush()

    for tag_id in {t for t in (field_tag_id, obstacle_tag_id) if t}:
        db.add(StoryTag(story_id=story.id, tag_id=tag_id))

    from app.services import consents as consents_service

    await consents_service.record(
        db, user.id, consents_service.KIND_PUBLICATION, note=f"story:{story.slug}"
    )
    return story


async def _display_name(db: AsyncSession, user: User) -> str:
    # имя героини истории: только имя из профиля, без email
    profile = await db.get(UserProfile, user.id)
    return (profile.display_name if profile else None) or "пользовательница"


async def _unique_slug(db: AsyncSession) -> str:
    import uuid as _uuid

    return f"story-{_uuid.uuid4().hex[:12]}"


async def pending_stories(db: AsyncSession) -> list[dict]:
    stories = (
        (
            await db.execute(
                select(Story)
                .where(Story.verification_status == VerificationStatus.PENDING)
                .order_by(Story.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    # источники одним запросом: у официальных сабмитов они приходят сразу
    from app.models import StorySource

    source_rows = (
        await db.execute(
            select(StorySource.story_id, StorySource.title, StorySource.url).where(
                StorySource.story_id.in_([s.id for s in stories])
            )
        )
    ).all()
    sources_by_story: dict = {}
    for story_id, title, url in source_rows:
        sources_by_story.setdefault(story_id, []).append({"title": title, "url": url})

    return [
        {
            "id": str(s.id),
            "slug": s.slug,
            "title": s.title,
            "text": s.full_text,
            "created_by": str(s.created_by) if s.created_by else None,
            "created_at": s.created_at,
            "story_type": s.story_type.value,
            "sources": sources_by_story.get(s.id, []),
        }
        for s in stories
    ]


async def publish_story(db: AsyncSession, story_id: str) -> bool:
    from datetime import UTC, datetime

    story = await _get_submission(db, story_id)
    if story is None:
        return False
    story.verification_status = VerificationStatus.VERIFIED
    story.publication_status = PublicationStatus.PUBLISHED
    story.published_at = datetime.now(UTC)
    db.add(story)
    return True


async def reject_story(db: AsyncSession, story_id: str) -> bool:
    story = await _get_submission(db, story_id)
    if story is None:
        return False
    author_id = story.created_by
    await db.delete(story)
    await db.flush()
    if author_id:
        author = await db.get(User, author_id)
        if author is not None:
            author.has_rejection_notice = True
            db.add(author)
    return True


async def _get_submission(db: AsyncSession, story_id: str):
    from uuid import UUID

    try:
        parsed = UUID(story_id)
    except ValueError:
        return None
    story = await db.get(Story, parsed)
    if story is None or story.verification_status != VerificationStatus.PENDING:
        return None
    return story


async def acknowledge_rejection(db: AsyncSession, user: User) -> None:
    user.has_rejection_notice = False
    db.add(user)
