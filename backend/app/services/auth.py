from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_token, new_session_token
from app.models import AuthIdentity, User, UserProfile, UserSession
from app.models.enums import UserRole

GOOGLE_PROVIDER = "google"


@dataclass(frozen=True)
class GoogleUserInfo:
    sub: str
    email: str
    name: str | None = None
    picture: str | None = None
    # google отдаёт флаг подтверждённости почты, пустым он быть не должен
    email_verified: bool = True


async def get_or_create_user(db: AsyncSession, info: GoogleUserInfo) -> User:
    # вход ищем по паре провайдер+sub, сам аккаунт не знает откуда человек вошёл
    identity = (
        await db.execute(
            select(AuthIdentity).where(
                AuthIdentity.provider == GOOGLE_PROVIDER,
                AuthIdentity.provider_sub == info.sub,
            )
        )
    ).scalar_one_or_none()

    if identity is None:
        user = User()
        db.add(user)
        await db.flush()

        db.add(
            AuthIdentity(
                user_id=user.id,
                provider=GOOGLE_PROVIDER,
                provider_sub=info.sub,
                email=info.email,
            )
        )
        db.add(
            UserProfile(
                user_id=user.id,
                # имя и аватар только начальное значение, дальше их редактирует сам
                display_name=info.name,
                avatar_url=info.picture,
            )
        )
        await db.flush()
        return user

    # забаненная не входит даже с новым входом
    user = await db.get(User, identity.user_id)
    if user is not None and user.is_banned:
        raise PermissionError("аккаунт заблокирован")

    # email у провайдера мог измениться, подтягиваем
    if identity.email != info.email:
        identity.email = info.email
        db.add(identity)

    # своё название профиля не затираем данными google
    profile = await db.get(UserProfile, identity.user_id)
    if profile is not None:
        if not profile.display_name and info.name:
            profile.display_name = info.name
            db.add(profile)
        if not profile.avatar_url and info.picture:
            profile.avatar_url = info.picture
            db.add(profile)

    return await db.get(User, identity.user_id)


async def promote_admin_if_listed(db: AsyncSession, user: User, provider_sub: str) -> None:
    # админа назначаем по google_sub из окружения, понижение роли вручную только в базе
    if provider_sub in get_settings().admin_subs and user.role != UserRole.ADMIN:
        user.role = UserRole.ADMIN
        db.add(user)
        await db.flush()


async def create_session(db: AsyncSession, user_id, user_agent: str | None) -> str:
    token = new_session_token()
    ttl = timedelta(days=get_settings().session_ttl_days)
    db.add(
        UserSession(
            token_hash=hash_token(token),
            user_id=user_id,
            user_agent=user_agent[:300] if user_agent else None,
            expires_at=datetime.now(UTC) + ttl,
        )
    )
    await db.flush()
    return token


async def get_user_by_token(db: AsyncSession, token: str) -> User | None:
    session = (
        await db.execute(select(UserSession).where(UserSession.token_hash == hash_token(token)))
    ).scalar_one_or_none()
    if session is None:
        return None

    now = datetime.now(UTC)
    if session.revoked_at is not None or session.expires_at <= now:
        return None

    user = await db.get(User, session.user_id)
    if user is None or user.is_banned:
        return None

    # скользящее продление: если осталось меньше половины срока подтягиваем вперёд
    remaining = session.expires_at - now
    if remaining < timedelta(days=get_settings().session_ttl_days) / 2:
        session.expires_at = now + timedelta(days=get_settings().session_ttl_days)
        db.add(session)
        await db.commit()

    return user


async def revoke_session(db: AsyncSession, token: str) -> None:
    await db.execute(
        update(UserSession)
        .where(UserSession.token_hash == hash_token(token), UserSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


async def purge_expired_sessions(db: AsyncSession) -> int:
    # протухшие сессии не нужны никому: их копить в базе смысла нет
    result = await db.execute(
        delete(UserSession).where(UserSession.expires_at <= datetime.now(UTC))
    )
    return result.rowcount or 0
