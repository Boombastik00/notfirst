from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request

from app.core.config import get_settings
from app.services.auth import GoogleUserInfo

oauth = OAuth()

oauth.register(
    name="google",
    client_id=get_settings().google_client_id,
    client_secret=get_settings().google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


def google_redirect_uri() -> str:
    # redirect_uri всегда виден браузеру поэтому строим от base_url а не от хоста api
    return f"{get_settings().base_url}/api/v1/auth/google/callback"


async def exchange_code(request: Request) -> GoogleUserInfo:
    # меняет код из ответа google на данные аккаунта
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo") or {}
    sub = userinfo.get("sub")
    email = userinfo.get("email")
    if not sub or not email:
        raise ValueError("google не вернул sub или email")
    return GoogleUserInfo(
        sub=sub,
        email=email,
        name=userinfo.get("name"),
        picture=userinfo.get("picture"),
        email_verified=bool(userinfo.get("email_verified", False)),
    )
