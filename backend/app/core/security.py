import hashlib
import secrets

from app.core.config import get_settings

# имя cookie с токеном сессии
SESSION_COOKIE = "nf_session"


def new_session_token() -> str:
    # сырой токен живёт только в cookie пользователя
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    # в базе хранится только хэш, утечка бд не даёт угнать сессии
    return hashlib.sha256(token.encode()).hexdigest()


def session_cookie_params() -> dict:
    settings = get_settings()
    return {
        "max_age": settings.session_ttl_days * 24 * 3600,
        "httponly": True,
        "samesite": "lax",
        "secure": settings.is_production,
        "path": "/",
    }
