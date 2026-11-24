import logging
import re
from urllib.parse import unquote, urlsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, PlainTextResponse, Response

from app.core.config import get_settings

MUTATING_METHODS = {"POST", "PATCH", "PUT", "DELETE"}

logger = logging.getLogger("honeypot")

# пасхалка: сигнатуры не появляются при обычной жизни (лаг/впн/опечатка),
# только при целененаправленных пробах сканеров и инъекциях
ATTACK_PATTERN = re.compile(
    r"(\.\./|\.\.\\|%2e%2e|etc/passwd|etc%2fpasswd|/\.env|\.git\b|\.aws\b|\.ssh\b"
    r"|wp-admin|wp-login|xmlrpc\.php|phpmyadmin|adminer|\.ds_store|\.bak\b"
    r"|<script|javascript:|onerror\s*=|onload\s*=\s*alert"
    r"|union\s+select|'\s*or\s*1\s*=\s*1|\"\s*or\s*\"\s*=\s*\"|sleep\s*\(\s*\d"
    r"|benchmark\s*\(|information_schema|load_file\s*\(|<\?php|/proc/self)",
    re.IGNORECASE,
)

RICKROLL_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


class HoneypotMiddleware(BaseHTTPMiddleware):
    # ловит явные проны сканеров: обход каталогов, инъекции, поиск конфигов
    # честных пользовательниц не задевает: их запросы таких сигнатур не содержат

    async def dispatch(self, request: Request, call_next) -> Response:
        raw = request.url.path + " " + (request.url.query or "")
        candidate = f"{raw} {unquote(raw)}"
        if ATTACK_PATTERN.search(candidate):
            client = request.client.host if request.client else "?"
            logger.warning("подозрительная активность: %s %s от %s", request.method, request.url.path, client)
            # эй, отстань :( ... и пусть песенка развеет боевой настрой
            return HTMLResponse(
                content=(
                    "<!doctype html><html lang='ru'><head><meta charset='utf-8'>"
                    "<meta http-equiv='refresh' content='2;url=" + RICKROLL_URL + "'>"
                    "<title>эй</title></head>"
                    "<body><p>эй, отстань :(</p>"
                    "<p><a href='" + RICKROLL_URL + "'>ладно, вот тебе песенка</a></p>"
                    "</body></html>"
                ),
                status_code=403,
            )
        return await call_next(request)

MUTATING_METHODS = {"POST", "PATCH", "PUT", "DELETE"}

# умеренная csp: без внешних источников, инлайн нужен админке и next
CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' https: data:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "object-src 'none'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    # базовые защитные заголовки на каждый ответ api и админки

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Content-Security-Policy", CSP)
        if get_settings().is_production:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.url.path.startswith("/api/"):
            # ответы с персональными данными не должны кэшироваться
            response.headers.setdefault("Cache-Control", "no-store")
        return response


class OriginCheckMiddleware(BaseHTTPMiddleware):
    # защита от csrf поверх samesite-cookie: браузер всегда присылает origin
    # на мутирующие запросы, чужой origin сразу режем

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in MUTATING_METHODS:
            origin = request.headers.get("origin")
            if origin:
                settings = get_settings()
                host = request.headers.get("host", "")
                origin_netloc = urlsplit(origin).netloc
                base_netloc = urlsplit(settings.base_url).netloc
                allowed = origin_netloc == host or origin_netloc == base_netloc
                if not allowed:
                    return PlainTextResponse("запрос с недопустимого источника", status_code=403)
        return await call_next(request)
