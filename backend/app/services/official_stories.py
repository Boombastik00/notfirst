import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Story, StorySource, User, UserProfile
from app.models.enums import (
    PublicationStatus,
    StoryType,
    VerificationStatus,
)

# официальная история авторки: после модерации становится проверенной биографией
# с подписью «авторка истории» и списком источников

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def _slugify(title: str) -> str:
    text = title.lower()
    text = "".join(TRANSLIT.get(ch, ch) for ch in text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:60] or "story"


async def _unique_slug(db: AsyncSession, base: str) -> str:
    slug = base
    counter = 1
    while True:
        exists = (
            await db.execute(select(Story.id).where(Story.slug == slug))
        ).scalar_one_or_none()
        if exists is None:
            return slug
        counter += 1
        slug = f"{base}-{counter}"


async def submit_official(
    db: AsyncSession,
    user: User,
    *,
    title: str,
    text: str,
    sources: list[dict],
) -> Story:
    title = title.strip()
    text = text.strip()
    if not title or len(title) > 200:
        raise HTTPException(status_code=400, detail="нужен заголовок до 200 символов")
    if len(text) < 200:
        raise HTTPException(
            status_code=400, detail="официальная история должна быть подробнее, хотя бы 200 символов"
        )
    if len(text) > 50000:
        raise HTTPException(status_code=400, detail="история слишком длинная")

    clean_sources = []
    for source in sources:
        s_title = (source.get("title") or "").strip()
        s_url = (source.get("url") or "").strip() or None
        if not s_title:
            continue
        clean_sources.append({"title": s_title[:300], "url": s_url})
    if not clean_sources:
        raise HTTPException(
            status_code=400, detail="у официальной истории должен быть хотя бы один источник"
        )

    profile = await db.get(UserProfile, user.id)
    display_name = (profile.display_name if profile else None) or "авторка"

    story = Story(
        slug=await _unique_slug(db, _slugify(title)),
        title=title,
        woman_name=display_name,
        short_description=text[:200].rsplit(" ", 1)[0] + "…",
        full_text=text,
        story_type=StoryType.VERIFIED_BIOGRAPHY,
        verification_status=VerificationStatus.PENDING,
        publication_status=PublicationStatus.DRAFT,
        is_anonymous=False,
        created_by=user.id,
    )
    db.add(story)
    await db.flush()

    for source in clean_sources:
        db.add(StorySource(story_id=story.id, **source))
    return story
