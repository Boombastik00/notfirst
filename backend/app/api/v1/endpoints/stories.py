from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_optional
from app.core.db import get_db
from app.models import User
from app.models.enums import StoryType
from app.schemas.story import StoryDetailOut, StoryListOut
from app.services import stories as story_service

router = APIRouter(tags=["stories"])


@router.get("/stories", response_model=StoryListOut)
async def list_stories(
    db: Annotated[AsyncSession, Depends(get_db)],
    q: Annotated[str | None, Query(max_length=100, description="поиск по заголовку, имени и описанию")] = None,
    country: Annotated[int | None, Query(description="тег страны")] = None,
    profession: Annotated[int | None, Query(description="тег профессии")] = None,
    field: Annotated[int | None, Query(description="тег сферы")] = None,
    obstacle: Annotated[int | None, Query(description="тег препятствия")] = None,
    theme: Annotated[int | None, Query(description="тег темы")] = None,
    story_type: Annotated[StoryType | None, Query(description="тип истории")] = None,
    sort: Annotated[Literal["new", "old", "title"], Query(description="сортировка")] = "new",
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> StoryListOut:
    data = await story_service.list_stories(
        db,
        q=q,
        filters={
            "country": country,
            "profession": profession,
            "field": field,
            "obstacle": obstacle,
            "theme": theme,
        },
        story_type=story_type,
        sort=sort,
        page=page,
        limit=limit,
    )
    return StoryListOut(**data)


@router.get("/stories/{slug}", response_model=StoryDetailOut)
async def get_story(
    slug: Annotated[str, Path(max_length=120)],
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User | None, Depends(get_current_user_optional)] = None,
) -> StoryDetailOut:
    data = await story_service.get_published_story(db, slug)
    if data is None:
        # неопубликованная история доступна только своей авторке
        if user is not None:
            own = await story_service.get_own_story(db, slug, user.id)
            if own is not None:
                return StoryDetailOut(**own)
        raise HTTPException(status_code=404, detail="история не найдена")
    return StoryDetailOut(**data)
