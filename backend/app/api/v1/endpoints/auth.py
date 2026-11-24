from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import SESSION_COOKIE, session_cookie_params
from app.models import AuthIdentity, User, UserProfile
from app.oauth import exchange_code, google_redirect_uri, oauth
from app.rate_limit import limiter
from app.schemas.user import UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google/start")
@limiter.limit("10/minute")
async def google_start(request: Request):
    settings = get_settings()
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="вход через google не настроен")

    # экран согласий передаёт версию принятых документов, запоминаем до коллбека
    consent_v = request.query_params.get("consent", "")
    if consent_v:
        request.session["consent_v"] = consent_v
    request.session["next"] = "/"
    return await oauth.google.authorize_redirect(request, google_redirect_uri())


@router.get("/google/callback")
@limiter.limit("10/minute")
async def google_callback(
    request: Request, db: Annotated[AsyncSession, Depends(get_db)]
):
    try:
        info = await exchange_code(request)
    except Exception as e:  # noqa: BLE001 - любой сбой обмена с google это одна и та же ошибка пользователя
        # причину пишем в лог чтобы диагностировать не вслепую
        import logging
        import traceback

        logging.getLogger("auth").error(
            "google exchange failed: %r\n%s", e, traceback.format_exc()
        )
        raise HTTPException(status_code=400, detail="не удалось завершить вход через google")

    if not info.email_verified:
        raise HTTPException(status_code=400, detail="подтвердите email в google и попробуйте снова")

    try:
        user = await auth_service.get_or_create_user(db, info)
    except PermissionError:
        raise HTTPException(status_code=403, detail="аккаунт заблокирован")

    await auth_service.promote_admin_if_listed(db, user, info.sub)

    # фиксируем принятые документы если экран согласий был пройден
    from app.services import consents as consents_service

    if request.session.get("consent_v"):
        await consents_service.record(db, user.id, consents_service.KIND_TERMS)
        await consents_service.record(db, user.id, consents_service.KIND_PD)
        request.session.pop("consent_v", None)

    token = await auth_service.create_session(db, user.id, request.headers.get("user-agent"))
    await db.commit()

    # без анкеты сначала на неё, дальше на главную
    destination = "/" if user.onboarding_completed else "/onboarding"
    response = RedirectResponse(url=destination, status_code=302)
    response.set_cookie(SESSION_COOKIE, token, **session_cookie_params())
    return response


@router.post("/logout", status_code=204)
@limiter.limit("30/minute")
async def logout(request: Request, db: Annotated[AsyncSession, Depends(get_db)]):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        await auth_service.revoke_session(db, token)
    # заодно выметаем просроченные сессии чтобы таблица не пухла
    await auth_service.purge_expired_sessions(db)
    await db.commit()

    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.get("/me", response_model=UserOut)
async def me(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserOut:
    # данные теперь разложены по трём таблицам: аккаунт, способ входа, профиль
    identity = (
        await db.execute(
            select(AuthIdentity).where(
                AuthIdentity.user_id == user.id,
                AuthIdentity.provider == auth_service.GOOGLE_PROVIDER,
            )
        )
    ).scalar_one_or_none()
    profile = await db.get(UserProfile, user.id)

    return UserOut(
        id=user.id,
        email=identity.email if identity else "",
        display_name=profile.display_name if profile else None,
        avatar_url=profile.avatar_url if profile else None,
        role=user.role.value,
        onboarding_completed=user.onboarding_completed,
        has_rejection_notice=user.has_rejection_notice,
        created_at=user.created_at,
    )
