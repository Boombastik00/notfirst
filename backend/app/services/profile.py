from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AuthIdentity, Tag, User, UserProfile, UserSelectedTag
from app.models.tag import TagGroup
from app.schemas.profile import OnboardingOptionsOut
from app.schemas.tag import TagOut
from app.services.auth import GOOGLE_PROVIDER
from app.services.tags import list_tags

# какие группы тегов валидны для каких полей профиля
FIELD_GROUPS = {
    "age_tag_id": "age_categories",
    "country_tag_id": "countries",
    "profession_tag_id": "professions",
    "current_field_tag_id": "fields",
}
# интересы пользовательницы: сферы и темы, но не сомнения
INTEREST_GROUPS = ("fields", "themes")
# на анкетировании спрашиваем только сферы, темы остаются в профиле
ONBOARDING_INTEREST_GROUPS = ("fields",)

OPTION_GROUPS = ("age_categories", "countries", "professions", "fields", "themes")


async def get_or_create_profile(db: AsyncSession, user: User) -> UserProfile:
    profile = await db.get(UserProfile, user.id)
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db.add(profile)
        await db.flush()
    return profile


async def _load_tag(db: AsyncSession, tag_id: int) -> Tag | None:
    return (
        await db.execute(
            select(Tag).options(selectinload(Tag.group)).where(Tag.id == tag_id, Tag.is_active)
        )
    ).scalar_one_or_none()


async def _validate_tag_field(db: AsyncSession, field: str, tag_id: int | None) -> Tag | None:
    # None допустим: необязательные поля можно очистить
    if tag_id is None:
        return None
    tag = await _load_tag(db, tag_id)
    expected_group = FIELD_GROUPS[field]
    if tag is None or tag.group.code != expected_group:
        raise HTTPException(
            status_code=400,
            detail=f"поле {field} ожидает тег из группы {expected_group}",
        )
    return tag


async def load_options(db: AsyncSession) -> OnboardingOptionsOut:
    by_group = {
        code: [tag for tag in await list_tags(db, code)]
        for code in OPTION_GROUPS
    }
    return OnboardingOptionsOut(**by_group)


async def current_state(db: AsyncSession, user: User) -> dict:
    profile = await get_or_create_profile(db, user)
    selected = (
        await db.execute(
            select(UserSelectedTag.tag_id).where(UserSelectedTag.user_id == user.id)
        )
    ).scalars().all()
    return {
        "age_tag_id": profile.age_tag_id,
        "country_tag_id": profile.country_tag_id,
        "profession_tag_id": profile.profession_tag_id,
        "current_field_tag_id": profile.current_field_tag_id,
        "interest_tag_ids": sorted(selected),
    }


async def save_onboarding(db: AsyncSession, user: User, payload) -> None:
    profile = await get_or_create_profile(db, user)

    if not payload.skip:
        if payload.age_tag_id is None:
            raise HTTPException(status_code=400, detail="укажите возрастную категорию")

        await _validate_tag_field(db, "age_tag_id", payload.age_tag_id)
        await _validate_tag_field(db, "country_tag_id", payload.country_tag_id)
        await _validate_tag_field(db, "profession_tag_id", payload.profession_tag_id)
        await _validate_tag_field(db, "current_field_tag_id", payload.current_field_tag_id)

        # категория до 18 включает младше 14, согласие представителя спрашиваем на всём диапазоне
        age_tag = await _load_tag(db, payload.age_tag_id)
        if age_tag is not None and age_tag.slug == "under-18":
            if not payload.parent_confirmed:
                raise HTTPException(
                    status_code=400,
                    detail="для аккаунтов младше 18 нужно согласие законного представителя",
                )
            from app.services import consents as consents_service

            await consents_service.record(db, user.id, consents_service.KIND_PARENTAL)

        profile.age_tag_id = payload.age_tag_id
        profile.country_tag_id = payload.country_tag_id
        profile.profession_tag_id = payload.profession_tag_id
        profile.current_field_tag_id = payload.current_field_tag_id
        db.add(profile)

        await set_interest_tags(db, user, payload.interest_tag_ids, ONBOARDING_INTEREST_GROUPS)

    # и после заполнения и после пропуска вопрос больше не навязываем
    user.onboarding_completed = True
    db.add(user)


async def update_profile(db: AsyncSession, user: User, payload) -> UserProfile:
    profile = await get_or_create_profile(db, user)
    changes = payload.model_dump(exclude_unset=True)

    for field, value in changes.items():
        if field in ("display_name", "bio"):
            setattr(profile, field, value)
            continue
        await _validate_tag_field(db, field, value)
        setattr(profile, field, value)

    db.add(profile)
    return profile


async def set_interest_tags(
    db: AsyncSession, user: User, tag_ids: list[int], groups: tuple[str, ...] = INTEREST_GROUPS
) -> None:
    # проверяем каждую метку: интересы это сферы и темы, не сомнения и не страны
    valid_ids = []
    for tag_id in tag_ids:
        tag = await _load_tag(db, tag_id)
        if tag is None or tag.group.code not in groups:
            raise HTTPException(
                status_code=400,
                detail="в интересах допустимы только сферы деятельности и темы",
            )
        valid_ids.append(tag_id)

    # убираем прежние интересы (только этих групп), сомнения если появятся не трогаем
    await db.execute(
        delete(UserSelectedTag).where(
            UserSelectedTag.user_id == user.id,
            UserSelectedTag.tag_id.in_(
                select(Tag.id)
                .join(TagGroup, TagGroup.id == Tag.group_id)
                .where(TagGroup.code.in_(INTEREST_GROUPS))
            ),
        )
    )
    for tag_id in sorted(set(valid_ids)):
        db.add(UserSelectedTag(user_id=user.id, tag_id=tag_id))


async def build_profile_out(db: AsyncSession, user: User) -> dict:
    profile = await get_or_create_profile(db, user)
    identity = (
        await db.execute(
            select(AuthIdentity).where(
                AuthIdentity.user_id == user.id,
                AuthIdentity.provider == GOOGLE_PROVIDER,
            )
        )
    ).scalar_one_or_none()

    async def tag_out(tag_id: int | None):
        if tag_id is None:
            return None
        tag = await _load_tag(db, tag_id)
        if tag is None:
            return None
        return TagOut.model_validate(tag)

    interests = [
        TagOut.model_validate(tag)
        for tag in (
            await db.execute(
                select(Tag)
                .options(selectinload(Tag.group))
                .join(UserSelectedTag, UserSelectedTag.tag_id == Tag.id)
                .where(UserSelectedTag.user_id == user.id)
                .order_by(Tag.group_id, Tag.sort_order)
            )
        ).scalars()
    ]

    return {
        "email": identity.email if identity else "",
        "display_name": profile.display_name,
        "avatar_url": profile.avatar_url,
        "bio": profile.bio,
        "age": await tag_out(profile.age_tag_id),
        "country": await tag_out(profile.country_tag_id),
        "profession": await tag_out(profile.profession_tag_id),
        "current_field": await tag_out(profile.current_field_tag_id),
        "interests": interests,
        "onboarding_completed": user.onboarding_completed,
    }


async def delete_account(db: AsyncSession, user: User) -> None:
    # каскад сам уносит профиль, интересы, сессии и избранное
    await db.delete(user)


async def acknowledge_rejection(db: AsyncSession, user: User) -> None:
    # пользовательница увидела уведомление об отклонении, убираем восклицательный знак
    user.has_rejection_notice = False
    db.add(user)
