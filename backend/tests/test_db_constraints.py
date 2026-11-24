from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import (
    AuthIdentity,
    Favorite,
    Story,
    StoryTag,
    Tag,
    TagGroup,
    User,
    UserProfile,
    UserSession,
)
from app.models.enums import StoryType


async def test_duplicate_tag_slug_in_group_rejected(db_session):
    group = (
        await db_session.execute(select(TagGroup).where(TagGroup.code == "professions"))
    ).scalar_one()
    duplicate = Tag(group_id=group.id, slug="medicine", name_ru="дубль")

    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_tag_delete_restricted_when_used_by_story(db_session):
    link = (await db_session.execute(select(StoryTag).limit(1))).scalar_one()
    tag = await db_session.get(Tag, link.tag_id)

    await db_session.delete(tag)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_tag_group_delete_restricted_when_has_tags(db_session):
    group = (
        await db_session.execute(select(TagGroup).where(TagGroup.code == "themes"))
    ).scalar_one()

    await db_session.delete(group)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_user_delete_cascades_and_nulls_story_author(db_session):
    user = User()
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        AuthIdentity(
            user_id=user.id,
            provider="google",
            provider_sub="sub-cascade",
            email="cascade@example.com",
        )
    )

    story = Story(
        slug="cascade-check",
        title="t",
        woman_name="n",
        short_description="s",
        full_text="f",
        story_type=StoryType.COMMUNITY_STORY,
        created_by=user.id,
    )
    db_session.add(story)
    db_session.add(
        UserSession(
            token_hash="x" * 64,
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
    )
    db_session.add(UserProfile(user_id=user.id))
    await db_session.flush()
    db_session.add(Favorite(user_id=user.id, story_id=story.id))
    await db_session.commit()

    await db_session.delete(user)
    await db_session.commit()

    # expire_on_commit=False поэтому обновляем объекты из базы вручную
    db_session.expire_all()

    # проверки в рамках конкретного пользователя, база общая для всех тестов
    user_id = user.id
    own_sessions = (
        await db_session.execute(select(UserSession).where(UserSession.user_id == user_id))
    ).scalars().first()
    own_profile = (
        await db_session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    ).scalars().first()
    own_favorites = (
        await db_session.execute(select(Favorite).where(Favorite.user_id == user_id))
    ).scalars().first()
    assert own_sessions is None
    assert own_profile is None
    assert own_favorites is None

    survived = (
        await db_session.execute(select(Story).where(Story.slug == "cascade-check"))
    ).scalar_one()
    assert survived.created_by is None
    assert survived.id == story.id


async def test_identity_provider_sub_unique(db_session):
    # один и тот же способ входа не может быть привязан к двум аккаунтам
    first = User()
    second = User()
    db_session.add_all([first, second])
    await db_session.flush()

    db_session.add_all(
        [
            AuthIdentity(
                user_id=first.id,
                provider="google",
                provider_sub="sub-same",
                email="one@example.com",
            ),
            AuthIdentity(
                user_id=second.id,
                provider="google",
                provider_sub="sub-same",
                email="two@example.com",
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_identity_deletes_with_user(db_session):
    # способ входа умирает вместе с аккаунтом
    user = User()
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        AuthIdentity(
            user_id=user.id, provider="google", provider_sub="sub-x", email="dup@example.com"
        )
    )
    await db_session.commit()

    await db_session.delete(user)
    await db_session.commit()
    db_session.expire_all()

    leftover = (
        await db_session.execute(
            select(AuthIdentity).where(AuthIdentity.provider_sub == "sub-x")
        )
    ).scalar_one_or_none()
    assert leftover is None


async def test_story_defaults_are_draft_and_pending(db_session):
    story = Story(
        slug="defaults-check",
        title="t",
        woman_name="n",
        short_description="s",
        full_text="f",
        story_type=StoryType.COMMUNITY_STORY,
    )
    db_session.add(story)
    await db_session.commit()

    fetched = (
        await db_session.execute(select(Story).where(Story.slug == "defaults-check"))
    ).scalar_one()
    assert fetched.publication_status.value == "draft"
    assert fetched.verification_status.value == "pending"
    assert fetched.created_by is None
