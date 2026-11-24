from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_ignore_empty=True, env_file=".env")

    # дефолты под локальную разработку без docker
    # 127.0.0.1 а не localhost: у docker бывают проблемы с ipv6-петлей ::1
    app_env: str = "local"
    database_url: str = "postgresql+asyncpg://notfirst:notfirst@127.0.0.1:5432/notfirst"

    # адрес который видит браузер, нужен для oauth redirect
    base_url: str = "http://localhost:3000"

    # google oauth, пустые значения значат что вход не настроен
    google_client_id: str = ""
    google_client_secret: str = ""

    # подпись короткоживущей state-cookie во время oauth handshake
    session_cookie_secret: str = "dev-insecure-change-me"

    # google_sub через запятую: кто из вошедших получает роль admin
    admin_google_subs: str = ""

    # срок жизни сессии
    session_ttl_days: int = 30

    @property
    def admin_subs(self) -> set[str]:
        return {sub.strip() for sub in self.admin_google_subs.split(",") if sub.strip()}

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
