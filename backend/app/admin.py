from pathlib import Path
from typing import ClassVar

from sqladmin import Admin, ModelView
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, RedirectResponse

from app.api.deps import STAFF_ROLES
from app.core import db as core_db
from app.core.config import get_settings
from app.core.security import SESSION_COOKIE
from app.models import AuthIdentity, Story, StorySource, Tag, TagGroup
from app.services import auth as auth_service


class AdminGateMiddleware(BaseHTTPMiddleware):
    # пропускает в /admin только вошедших с ролью персонала
    # проверка на бэкенде независимо от того что рисует интерфейс

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/admin") or path.startswith("/admin/statics"):
            return await call_next(request)

        token = request.cookies.get(SESSION_COOKIE)
        user = None
        if token:
            async with core_db.session_factory() as session:
                user = await auth_service.get_user_by_token(session, token)

        if user is None:
            # на страницу входа фронтенда: относительный /login здесь оказался бы
            # битым при заходе напрямую на порт api
            return RedirectResponse(url=f"{get_settings().base_url}/login", status_code=302)
        if user.role not in STAFF_ROLES:
            return PlainTextResponse("недостаточно прав для административного раздела", status_code=403)

        return await call_next(request)


class StoryAdmin(ModelView, model=Story):
    name = "История"
    name_plural = "Истории"
    column_list: ClassVar = [
        Story.title,
        Story.woman_name,
        Story.story_type,
        Story.verification_status,
        Story.publication_status,
        Story.slug,
    ]
    column_labels: ClassVar = {
        "title": "заголовок",
        "woman_name": "имя героини",
        "story_type": "тип (каталог или официальная)",
        "verification_status": "статус проверки (менять через модерацию на сайте)",
        "publication_status": "статус публикации (менять через модерацию на сайте)",
        "slug": "адрес страницы (slug)",
    }


class TagAdmin(ModelView, model=Tag):
    name = "Тег"
    name_plural = "Теги"
    column_list: ClassVar = [Tag.group, Tag.parent_id, Tag.slug, Tag.name_ru, Tag.is_active, Tag.sort_order]
    column_labels: ClassVar = {
        "group": "группа",
        "parent_id": "родитель",
        "slug": "slug",
        "name_ru": "название",
        "is_active": "активен",
        "sort_order": "порядок",
    }


class TagGroupAdmin(ModelView, model=TagGroup):
    name = "Группа тегов"
    name_plural = "Группы тегов"
    column_list: ClassVar = [TagGroup.code, TagGroup.name_ru, TagGroup.sort_order, TagGroup.is_system]
    column_labels: ClassVar = {"code": "код", "name_ru": "название", "sort_order": "порядок", "is_system": "системная"}


class StorySourceAdmin(ModelView, model=StorySource):
    name = "Источник"
    name_plural = "Источники"
    column_list: ClassVar = [StorySource.story_id, StorySource.title, StorySource.url, StorySource.source_type]
    column_labels: ClassVar = {
        "story_id": "история",
        "title": "название",
        "url": "ссылка",
        "source_type": "тип",
    }


class AuthIdentityAdmin(ModelView, model=AuthIdentity):
    name = "Способ входа"
    name_plural = "Способы входа"
    column_list: ClassVar = [
        AuthIdentity.user_id,
        AuthIdentity.provider,
        AuthIdentity.provider_sub,
        AuthIdentity.email,
    ]
    column_labels: ClassVar = {
        "user_id": "аккаунт",
        "provider": "провайдер",
        "provider_sub": "id у провайдера",
        "email": "email",
    }


_admin_setup_done = False


def setup_admin(app) -> None:
    # защищаемся от повторного монтирования при пересоздании приложения в тестах
    global _admin_setup_done
    if _admin_setup_done:
        return
    _admin_setup_done = True

    templates_dir = str(Path(__file__).parent / "admin_templates")
    admin = Admin(
        app,
        engine=core_db.engine,
        base_url="/admin",
        templates_dir=templates_dir,
        title="не первая · панель персонала",
    )
    # адрес пользовательской части для кнопки «вернуться на сайт» в шаблоне
    admin.site_url = get_settings().base_url
    admin.add_view(StoryAdmin)
    admin.add_view(TagAdmin)
    admin.add_view(TagGroupAdmin)
    admin.add_view(StorySourceAdmin)
    admin.add_view(AuthIdentityAdmin)
