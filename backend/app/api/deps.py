from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import SESSION_COOKIE
from app.models import User
from app.models.enums import UserRole
from app.services import auth as auth_service


async def get_current_user(
    request: Request, db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="требуется вход")

    user = await auth_service.get_user_by_token(db, token)
    if user is None:
        raise HTTPException(status_code=401, detail="сессия недействительна")

    return user


async def get_current_user_optional(
    request: Request, db: Annotated[AsyncSession, Depends(get_db)]
) -> User | None:
    # как get_current_user но гость получает None вместо 401
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    return await auth_service.get_user_by_token(db, token)


def require_role(*roles: UserRole):
    async def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="недостаточно прав")
        return user

    return checker


STAFF_ROLES = (UserRole.ADMIN, UserRole.EDITOR, UserRole.MODERATOR)
