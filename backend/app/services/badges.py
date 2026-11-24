from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserBadge
from app.models.enums import UserRole

# префиксы: код -> человеческое название и роль которая требуется
BADGES = {
    "creator": {"label": "создательница", "role": UserRole.ADMIN},
    "moderator": {"label": "модераторша", "role": UserRole.MODERATOR},
    "author": {"label": "авторка", "role": UserRole.EDITOR},
    "developer": {"label": "разработчица", "role": None},
    "designer": {"label": "дизайнерка", "role": None},
}

# кто какие бейджи может выдавать
GRANTABLE_BY = {
    UserRole.ADMIN: set(BADGES),
    UserRole.MODERATOR: {"moderator", "author", "developer", "designer"},
    UserRole.EDITOR: set(),
    UserRole.USER: set(),
}

ROLE_PRIORITY = {
    UserRole.USER: 0,
    UserRole.MODERATOR: 1,
    UserRole.EDITOR: 1,
    UserRole.ADMIN: 2,
}


async def badges_of(db: AsyncSession, user_id) -> list[str]:
    rows = (
        await db.execute(select(UserBadge.badge).where(UserBadge.user_id == user_id))
    ).scalars().all()
    return list(rows)


async def grant(
    db: AsyncSession, actor: User, target_id: UUID, badge: str
) -> None:
    if badge not in BADGES:
        raise HTTPException(status_code=400, detail="неизвестный префикс")
    if badge not in GRANTABLE_BY.get(actor.role, set()):
        raise HTTPException(status_code=403, detail="этот префикс вам выдавать нельзя")

    target = await db.get(User, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="пользовательница не найдена")
    if target.role == UserRole.ADMIN and actor.role != UserRole.ADMIN:
        # создательницу не трогает никто кроме создательницы
        raise HTTPException(status_code=403, detail="нельзя менять префиксы создательницы")

    existing = (
        await db.execute(
            select(UserBadge).where(UserBadge.user_id == target_id, UserBadge.badge == badge)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return  # уже есть, повторная выдача безвредна

    db.add(UserBadge(user_id=target_id, badge=badge, granted_by=actor.id))

    required_role = BADGES[badge]["role"]
    if required_role is not None and ROLE_PRIORITY[target.role] < ROLE_PRIORITY[required_role]:
        target.role = required_role
        db.add(target)


async def revoke(db: AsyncSession, actor: User, target_id: UUID, badge: str) -> None:
    if badge not in BADGES:
        raise HTTPException(status_code=400, detail="неизвестный префикс")
    if badge not in GRANTABLE_BY.get(actor.role, set()):
        raise HTTPException(status_code=403, detail="этот префикс вам снимать нельзя")

    target = await db.get(User, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="пользовательница не найдена")
    if target.role == UserRole.ADMIN and actor.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="нельзя менять префиксы создательницы")

    await db.execute(
        delete(UserBadge).where(UserBadge.user_id == target_id, UserBadge.badge == badge)
    )
    # роль не понижаем: пусть разбирается создательница вручную


async def ban_user(db: AsyncSession, actor: User, target_id: UUID) -> None:
    target = await db.get(User, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="пользовательница не найдена")
    if target.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="создательницу забанить нельзя")
    if actor.role != UserRole.ADMIN and ROLE_PRIORITY[target.role] >= ROLE_PRIORITY[actor.role]:
        raise HTTPException(status_code=403, detail="нельзя банить равную или старше по роли")

    target.is_banned = True
    db.add(target)
    # все её сессии умирают сразу
    from app.models import UserSession

    await db.execute(delete(UserSession).where(UserSession.user_id == target_id))


async def unban_user(db: AsyncSession, actor: User, target_id: UUID) -> None:
    target = await db.get(User, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="пользовательница не найдена")
    target.is_banned = False
    db.add(target)
