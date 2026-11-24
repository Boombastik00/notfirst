from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.admin import AdminGateMiddleware, setup_admin
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.middlewares import (
    HoneypotMiddleware,
    OriginCheckMiddleware,
    SecurityHeadersMiddleware,
)
from app.rate_limit import limiter


def create_app() -> FastAPI:
    settings = get_settings()

    # лучше упасть на старте чем подписывать state-cookie известным всем значением
    if settings.is_production and settings.session_cookie_secret == "dev-insecure-change-me":
        raise RuntimeError("SESSION_COOKIE_SECRET не задан в production")

    # в production схему api наружу не отдаём
    is_prod = settings.is_production
    app = FastAPI(
        title="не первая api",
        version="0.1.0",
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
        openapi_url=None if is_prod else "/openapi.json",
    )

    app.state.limiter = limiter

    async def _too_many(request, exc):
        return JSONResponse({"detail": "слишком много запросов, попробуйте позже"}, status_code=429)

    app.add_exception_handler(RateLimitExceeded, _too_many)

    # порядок add = обратный порядок выполнения, заголовки должны быть самыми внешними
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(SessionMiddleware, secret_key=settings.session_cookie_secret)
    app.add_middleware(OriginCheckMiddleware)
    app.add_middleware(AdminGateMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    # медовуха поверх всего: перехватывает проны сканеров раньше прочих проверок
    app.add_middleware(HoneypotMiddleware)

    app.include_router(api_router, prefix="/api/v1")

    # корень api ведёт на сайт: случайно зашедшая на порт 8000 попадает куда надо
    @app.get("/", include_in_schema=False)
    async def root_redirect():
        return RedirectResponse(url=settings.base_url)

    setup_admin(app)
    return app


app = create_app()
