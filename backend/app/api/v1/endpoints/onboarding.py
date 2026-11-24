from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import User
from app.rate_limit import limiter
from app.schemas.profile import OnboardingIn, OnboardingOut
from app.services import profile as profile_service

router = APIRouter(tags=["onboarding"])


@router.get("/onboarding", response_model=OnboardingOut)
async def get_onboarding(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OnboardingOut:
    options = await profile_service.load_options(db)
    current = await profile_service.current_state(db, user)
    return OnboardingOut(
        already_completed=user.onboarding_completed,
        options=options,
        current=current,
    )


@router.post("/onboarding", status_code=204)
@limiter.limit("20/minute")
async def post_onboarding(
    request: Request,
    payload: OnboardingIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await profile_service.save_onboarding(db, user, payload)
    await db.commit()
