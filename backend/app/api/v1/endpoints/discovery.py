from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import User
from app.rate_limit import limiter
from app.schemas.discovery import (
    DailyOut,
    PendingStoryOut,
    RecommendationOut,
    StoryCardFull,
    SubmitOfficialIn,
    SubmitStoryIn,
)
from app.services import discovery as discovery_service

router = APIRouter(tags=["discovery"])


def _staff_dep():
    from app.api.deps import require_role
    from app.models.enums import UserRole

    return require_role(UserRole.ADMIN, UserRole.EDITOR, UserRole.MODERATOR)


@router.get("/stories/daily", response_model=DailyOut)
async def story_of_the_day(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DailyOut:
    story = await discovery_service.story_of_the_day(db)
    if story is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="историй пока нет")
    return DailyOut(story=StoryCardFull(**story))


@router.get("/stories/random", response_model=RecommendationOut)
async def random_story(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RecommendationOut:
    # случайная по известному из профиля, иначе совсем случайная
    from app.models import UserProfile

    profile = await db.get(UserProfile, user.id)
    story = await discovery_service.random_story(
        db,
        age_tag_id=profile.age_tag_id if profile else None,
        country_tag_id=profile.country_tag_id if profile else None,
    )
    return RecommendationOut(story=StoryCardFull(**story) if story else None, random=True)


@router.get("/recommendations", response_model=RecommendationOut)
@limiter.limit("30/minute")
async def recommend(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    profession: Annotated[int | None, Query(description="тег профессии из ответа")] = None,
    field: Annotated[int | None, Query(description="тег сферы из ответа")] = None,
    obstacle: Annotated[
        list[int] | None, Query(description="теги сомнений, можно несколько")
    ] = None,
    community_only: bool = False,
) -> RecommendationOut:
    result = await discovery_service.recommend(
        db,
        profession_tag_id=profession,
        field_tag_id=field,
        obstacle_tag_ids=obstacle,
        community_only=community_only,
        user_id=user.id,
    )
    if result is None:
        return RecommendationOut()
    from app.schemas.discovery import FeedItem, MatchReason

    return RecommendationOut(
        feed=[
            FeedItem(
                story=StoryCardFull(**item["story"]),
                match_reasons=[MatchReason(**r) for r in item["match_reasons"]],
                random=item["random"],
            )
            for item in result["feed"]
        ],
    )


@router.post("/stories/submit", status_code=202)
@limiter.limit("5/hour")
async def submit_story(
    request: Request,
    payload: SubmitStoryIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.services import submissions as submissions_service

    story = await submissions_service.submit_story(
        db,
        user,
        text=payload.text,
        title=payload.title,
        field_tag_id=payload.field_tag_id,
        profession_tag_id=payload.profession_tag_id,
        obstacle_tag_id=payload.obstacle_tag_id,
        consent_publication=payload.consent_publication,
    )
    await db.commit()
    return {"detail": "спасибо, история отправлена на модерацию", "slug": story.slug}


def _author_dep():
    from app.api.deps import require_role
    from app.models.enums import UserRole

    # официальные истории пишут авторки и выше
    return require_role(UserRole.ADMIN, UserRole.EDITOR)


@router.post("/stories/official", status_code=202)
@limiter.limit("10/hour")
async def submit_official(
    request: Request,
    payload: SubmitOfficialIn,
    user: Annotated[User, Depends(_author_dep())],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.services import official_stories as official_service

    story = await official_service.submit_official(
        db,
        user,
        title=payload.title,
        text=payload.text,
        sources=[s.model_dump() for s in payload.sources],
    )
    await db.commit()
    return {"detail": "спасибо, официальная история отправлена на модерацию", "slug": story.slug}


@router.get("/moderation/pending", response_model=list[PendingStoryOut])
async def get_pending(
    user: Annotated[User, Depends(_staff_dep())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PendingStoryOut]:
    from app.services import submissions as submissions_service

    return [PendingStoryOut(**s) for s in await submissions_service.pending_stories(db)]


@router.post("/moderation/{story_id}/publish", status_code=204)
async def publish(
    story_id: str,
    user: Annotated[User, Depends(_staff_dep())],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.services import submissions as submissions_service

    if not await submissions_service.publish_story(db, story_id):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="история не найдена или уже обработана")
    await db.commit()
    return Response(status_code=204)


@router.post("/moderation/{story_id}/reject", status_code=204)
async def reject(
    story_id: str,
    user: Annotated[User, Depends(_staff_dep())],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from app.services import submissions as submissions_service

    if not await submissions_service.reject_story(db, story_id):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="история не найдена или уже обработана")
    await db.commit()
    return Response(status_code=204)
