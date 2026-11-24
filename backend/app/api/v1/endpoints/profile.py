from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.security import SESSION_COOKIE
from app.models import User
from app.rate_limit import limiter
from app.schemas.my_stories import MyStoriesOut
from app.schemas.profile import InterestsUpdateIn, ProfileOut, ProfileUpdateIn
from app.services import my_stories as my_stories_service
from app.services import profile as profile_service

router = APIRouter(tags=["profile"])


@router.get("/profile", response_model=ProfileOut)
async def get_profile(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileOut:
    data = await profile_service.build_profile_out(db, user)
    return ProfileOut(**data)


@router.patch("/profile", response_model=ProfileOut)
@limiter.limit("30/minute")
async def patch_profile(
    request: Request,
    payload: ProfileUpdateIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileOut:
    await profile_service.update_profile(db, user, payload)
    await db.commit()
    await db.refresh(user)

    data = await profile_service.build_profile_out(db, user)
    return ProfileOut(**data)


@router.put("/profile/tags", response_model=ProfileOut)
@limiter.limit("30/minute")
async def put_profile_tags(
    request: Request,
    payload: InterestsUpdateIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileOut:
    await profile_service.set_interest_tags(db, user, payload.tag_ids)
    await db.commit()

    data = await profile_service.build_profile_out(db, user)
    return ProfileOut(**data)


@router.get("/profile/stories", response_model=MyStoriesOut)
async def get_my_stories(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MyStoriesOut:
    # авторка видит свои истории в любом статусе включая черновики
    items = await my_stories_service.list_my_stories(db, user.id)
    return MyStoriesOut(items=items, total=len(items))


@router.post("/profile/acknowledge-rejection", status_code=204)
async def acknowledge_rejection(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # пользовательница увидела печальное уведомление — убираем его навсегда
    await profile_service.acknowledge_rejection(db, user)
    await db.commit()
    return Response(status_code=204)


@router.post("/account/delete", status_code=204)
@limiter.limit("5/minute")
async def delete_account(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # безвозвратно: профиль, интересы, избранное и сессии уходят каскадом
    await profile_service.delete_account(db, user)
    await db.commit()

    resp = Response(status_code=204)
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp
