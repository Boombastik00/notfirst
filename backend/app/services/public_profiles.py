from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Story, Tag, User, UserBadge, UserProfile
from app.models.enums import PublicationStatus, VerificationStatus
from app.services.badges import BADGES


async def search_public_profiles(db: AsyncSession, query: str, limit: int = 20) -> list[dict]:
    # ник — это имя из профиля; email в поиске не участвует и не показывается
    from app.services.stories import sanitize_query

    query = sanitize_query(query)
    if not query:
        return []
    pattern = f"%{query}%"
    name = func.coalesce(UserProfile.display_name, "")

    rows = (
        await db.execute(
            select(User.id, name.label("display_name"), UserProfile.avatar_url)
            .outerjoin(UserProfile, UserProfile.user_id == User.id)
            .where(User.is_banned.is_(False), name.ilike(pattern))
            .order_by(func.lower(name))
            .limit(limit)
        )
    ).all()

    if not rows:
        return []

    badge_rows = (
        await db.execute(
            select(UserBadge.user_id, UserBadge.badge).where(
                UserBadge.user_id.in_([r.id for r in rows])
            )
        )
    ).all()
    badges_by_user: dict = {}
    for user_id, badge in badge_rows:
        if badge in BADGES:
            badges_by_user.setdefault(str(user_id), []).append(badge)

    return [
        {
            "id": str(r.id),
            "display_name": r.display_name,
            "avatar_url": r.avatar_url,
            "badges": [
                {"code": code, "label": BADGES[code]["label"]}
                for code in badges_by_user.get(str(r.id), [])
            ],
            "is_banned": False,
        }
        for r in rows
    ]


async def public_profile(db: AsyncSession, user_id: UUID) -> dict | None:
    user = await db.get(User, user_id)
    if user is None:
        return None
    profile = await db.get(UserProfile, user_id)

    badge_rows = (
        await db.execute(select(UserBadge.badge).where(UserBadge.user_id == user_id))
    ).scalars().all()

    return {
        "id": str(user_id),
        "display_name": (profile.display_name if profile else None)
        or "пользовательница",
        "avatar_url": profile.avatar_url if profile else None,
        "badges": [
            {"code": code, "label": BADGES[code]["label"]}
            for code in badge_rows
            if code in BADGES
        ],
        "is_banned": user.is_banned,
    }


async def public_stories(db: AsyncSession, user_id: UUID) -> list[dict]:
    stories = (
        (
            await db.execute(
                select(Story)
                .where(
                    Story.created_by == user_id,
                    Story.publication_status == PublicationStatus.PUBLISHED,
                    Story.verification_status == VerificationStatus.VERIFIED,
                )
                .order_by(Story.published_at.desc())
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
            "is_anonymous": s.is_anonymous,
            "country": names.get(s.country_tag_id),
            "profession": names.get(s.profession_tag_id),
        }
        for s in stories
    ]
