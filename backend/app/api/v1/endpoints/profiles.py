from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.db import get_db
from app.models import User
from app.models.enums import UserRole
from app.rate_limit import limiter
from app.schemas.badges import BadgesCatalogOut
from app.schemas.public_profile import (
    BadgeIn,
    PublicProfileOut,
    PublicStoriesOut,
)
from app.services import badges as badges_service
from app.services import public_profiles as public_service

router = APIRouter(prefix="/u", tags=["profiles"])

# выдача и баны доступны модераторкам и выше
staff = require_role(UserRole.ADMIN, UserRole.MODERATOR)


@router.get("/badges", response_model=BadgesCatalogOut)
async def badges_catalog() -> BadgesCatalogOut:
    from app.services.badges import BADGES

    return BadgesCatalogOut(
        items=[
            {"code": code, "label": meta["label"]} for code, meta in BADGES.items()
        ]
    )


@router.get("/search", response_model=list[PublicProfileOut])
@limiter.limit("30/minute")
async def search_profiles(
    request: Request,
    q: Annotated[str, Query(min_length=2, max_length=100, description="часть ника")],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[PublicProfileOut]:
    items = await public_service.search_public_profiles(db, q)
    return [PublicProfileOut(**item) for item in items]


@router.get("/{user_id}", response_model=PublicProfileOut)
async def get_public_profile(
    user_id: Annotated[UUID, Path()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicProfileOut:
    data = await public_service.public_profile(db, user_id)
    if data is None:
        raise HTTPException(status_code=404, detail="профиль не найден")
    return PublicProfileOut(**data)


@router.get("/{user_id}/stories", response_model=PublicStoriesOut)
async def get_public_stories(
    user_id: Annotated[UUID, Path()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicStoriesOut:
    items = await public_service.public_stories(db, user_id)
    return PublicStoriesOut(items=items, total=len(items))


@router.post("/{user_id}/badges", status_code=204)
@limiter.limit("30/minute")
async def grant_badge(
    request: Request,
    user_id: Annotated[UUID, Path()],
    payload: BadgeIn,
    actor: Annotated[User, Depends(staff)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await badges_service.grant(db, actor, user_id, payload.badge)
    await db.commit()
    return Response(status_code=204)


@router.delete("/{user_id}/badges/{badge}", status_code=204)
@limiter.limit("30/minute")
async def revoke_badge(
    request: Request,
    user_id: Annotated[UUID, Path()],
    badge: str,
    actor: Annotated[User, Depends(staff)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await badges_service.revoke(db, actor, user_id, badge)
    await db.commit()
    return Response(status_code=204)


@router.post("/{user_id}/ban", status_code=204)
@limiter.limit("10/minute")
async def ban(
    request: Request,
    user_id: Annotated[UUID, Path()],
    actor: Annotated[User, Depends(staff)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await badges_service.ban_user(db, actor, user_id)
    await db.commit()
    return Response(status_code=204)


@router.delete("/{user_id}/ban", status_code=204)
@limiter.limit("10/minute")
async def unban(
    request: Request,
    user_id: Annotated[UUID, Path()],
    actor: Annotated[User, Depends(staff)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await badges_service.unban_user(db, actor, user_id)
    await db.commit()
    return Response(status_code=204)

