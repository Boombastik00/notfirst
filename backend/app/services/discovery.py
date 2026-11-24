import hashlib
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Story, StoryTag, Tag, TagGroup, UserProfile
from app.models.enums import PublicationStatus, StoryType, VerificationStatus

PUBLISHED = (
    Story.publication_status == PublicationStatus.PUBLISHED,
    Story.verification_status == VerificationStatus.VERIFIED,
)

# веса совпадений для подбора: сомнение самое важное
WEIGHTS = {
    "obstacle": 10,
    "profession": 6,
    "field": 5,
    "age": 4,
    "country": 2,
}

REASON_TEMPLATES = {
    "obstacle": "героиня сталкивалась с тем же сомнением",
    "profession": "героиня в той же профессии",
    "field": "история из близкой тебе сферы",
    "age": "героиня в твоей возрастной категории",
    "country": "героиня из твоей страны",
}


async def story_of_the_day(db: AsyncSession) -> dict | None:
    # детерминированная ротация: один и тот же день = одна и та же история для всех
    stories = (
        (await db.execute(select(Story.id).where(*PUBLISHED).order_by(Story.id))).scalars().all()
    )
    if not stories:
        return None
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    digest = hashlib.sha256(f"{day}".encode()).hexdigest()
    picked = stories[int(digest, 16) % len(stories)]
    row = (
        await db.execute(select(Story).where(Story.id == picked))
    ).scalar_one()
    return _card(row, await _names(db, [row]))


async def random_story(db: AsyncSession, *, age_tag_id=None, country_tag_id=None) -> dict | None:
    stmt = select(Story).where(*PUBLISHED)
    if age_tag_id:
        stmt = stmt.where(Story.age_tag_id == age_tag_id)
    if country_tag_id:
        stmt = stmt.where(Story.country_tag_id == country_tag_id)
    story = (
        (await db.execute(stmt.order_by(func.random()).limit(1))).scalars().first()
    )
    if story is None and (age_tag_id or country_tag_id):
        # слишком узко — расслабляем фильтры
        story = (
            (await db.execute(select(Story).where(*PUBLISHED).order_by(func.random()).limit(1)))
            .scalars()
            .first()
        )
    if story is None:
        return None
    return _card(story, await _names(db, [story]))


async def _names(db: AsyncSession, stories) -> dict:
    tag_ids = set()
    for s in stories:
        tag_ids.update({s.country_tag_id, s.profession_tag_id})
    tag_ids.discard(None)
    if not tag_ids:
        return {}
    rows = (await db.execute(select(Tag.id, Tag.name_ru).where(Tag.id.in_(tag_ids)))).all()
    return dict(rows)


def _card(s: Story, names: dict) -> dict:
    return {
        "slug": s.slug,
        "title": s.title,
        "woman_name": s.woman_name,
        "short_description": s.short_description,
        "full_text": s.full_text,
        "story_type": s.story_type.value,
        "is_anonymous": s.is_anonymous,
        "country": names.get(s.country_tag_id),
        "profession": names.get(s.profession_tag_id),
    }


async def recommend(
    db: AsyncSession,
    *,
    profession_tag_id: int | None = None,
    field_tag_id: int | None = None,
    obstacle_tag_ids: list[int] | None = None,
    community_only: bool = False,
    user_id=None,
) -> dict | None:
    """подбор по ответам мастера переживания.

    сомнений можно выбрать несколько — каждое совпадение считается отдельно.
    возраст и страна подтягиваются из профиля чтобы не спрашивать лишнее.
    """
    profile = await db.get(UserProfile, user_id) if user_id else None

    stmt = select(Story).where(*PUBLISHED)
    if community_only:
        stmt = stmt.where(Story.story_type == StoryType.COMMUNITY_STORY)

    stories = (await db.execute(stmt)).scalars().all()
    if not stories:
        return None

    # теги историй одним запросом
    story_ids = [s.id for s in stories]
    tag_rows = (
        await db.execute(
            select(StoryTag.story_id, Tag.id, TagGroup.code, Tag.name_ru)
            .join(Tag, Tag.id == StoryTag.tag_id)
            .join(TagGroup, TagGroup.id == Tag.group_id)
            .where(StoryTag.story_id.in_(story_ids))
        )
    ).all()
    tags_by_story: dict = {}
    for story_id, tag_id, group_code, name in tag_rows:
        tags_by_story.setdefault(story_id, []).append((tag_id, group_code, name))

    def score(s: Story) -> tuple[int, list[dict]]:
        points = 0
        reasons = []
        tags = tags_by_story.get(s.id, [])
        if obstacle_tag_ids:
            for tag_id, group, name in tags:
                if group == "obstacles" and tag_id in obstacle_tag_ids:
                    points += WEIGHTS["obstacle"]
                    reasons.append(
                        {"dimension": "obstacle", "text": REASON_TEMPLATES["obstacle"], "tag": name}
                    )
        if profession_tag_id and s.profession_tag_id == profession_tag_id:
            points += WEIGHTS["profession"]
            reasons.append({"dimension": "profession", "text": REASON_TEMPLATES["profession"], "tag": None})
        if field_tag_id:
            for tag_id, group, name in tags:
                if group == "fields" and tag_id == field_tag_id:
                    points += WEIGHTS["field"]
                    reasons.append({"dimension": "field", "text": REASON_TEMPLATES["field"], "tag": name})
        if profile:
            if profile.age_tag_id and s.age_tag_id == profile.age_tag_id:
                points += WEIGHTS["age"]
                reasons.append({"dimension": "age", "text": REASON_TEMPLATES["age"], "tag": None})
            if profile.country_tag_id and s.country_tag_id == profile.country_tag_id:
                points += WEIGHTS["country"]
                reasons.append({"dimension": "country", "text": REASON_TEMPLATES["country"], "tag": None})
        return points, reasons

    ranked = sorted(((score(s), s) for s in stories), key=lambda pair: (-pair[0][0], pair[1].slug))

    # лента по убыванию совпадений: сомнения > профессия > сфера > страна > возраст
    names = await _names(db, [s for _, s in ranked])
    feed = [
        {
            "story": _card(s, names),
            "match_reasons": reasons,
            "random": False,
        }
        for (points, reasons), s in ranked
        if points > 0
    ]

    if not feed:
        # совсем без совпадений: случайная по профилю с честной пометкой
        extra = await random_story(
            db, age_tag_id=profile.age_tag_id if profile else None,
            country_tag_id=profile.country_tag_id if profile else None,
        )
        return {"feed": [{"story": extra, "match_reasons": [], "random": True}] if extra else []}

    # за последней совпавшей — просто вдохновляющие случайные, без претензии на совпадение
    seen = {item["story"]["slug"] for item in feed}
    inspiration = (
        await db.execute(
            select(Story)
            .where(*PUBLISHED, Story.slug.not_in(seen))
            .order_by(func.random())
            .limit(10)
        )
    ).scalars().all()
    ins_names = await _names(db, inspiration)
    feed.extend(
        {"story": _card(s, ins_names), "match_reasons": [], "random": True} for s in inspiration
    )

    return {"feed": feed}
