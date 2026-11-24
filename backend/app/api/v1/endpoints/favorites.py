from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models import User
from app.models.enums import StoryType
from app.rate_limit import limiter
from app.schemas.favorite import FavoriteListOut
from app.services import favorites as favorite_service

router = APIRouter(tags=["favorites"])


@router.get("/favorites", response_model=FavoriteListOut)
async def get_favorites(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    q: Annotated[str | None, Query(max_length=100)] = None,
    country: Annotated[int | None, Query(description="тег страны")] = None,
    profession: Annotated[int | None, Query(description="тег профессии")] = None,
    field: Annotated[int | None, Query(description="тег сферы")] = None,
    obstacle: Annotated[int | None, Query(description="тег препятствия")] = None,
    theme: Annotated[int | None, Query(description="тег темы")] = None,
    story_type: Annotated[StoryType | None, Query(description="тип истории")] = None,
    sort: Annotated[
        Literal["saved", "new", "old", "title"], Query(description="сортировка")
    ] = "saved",
) -> FavoriteListOut:
    items = await favorite_service.list_favorites(
        db,
        user.id,
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
    )
    return FavoriteListOut(items=items, total=len(items))


@router.put("/favorites/{slug}", status_code=204)
@limiter.limit("60/minute")
async def put_favorite(
    request: Request,
    slug: Annotated[str, Path(max_length=120)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await favorite_service.add_favorite(db, user.id, slug)
    await db.commit()
    return Response(status_code=204)


@router.delete("/favorites/{slug}", status_code=204)
@limiter.limit("60/minute")
async def delete_favorite(
    request: Request,
    slug: Annotated[str, Path(max_length=120)],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await favorite_service.remove_favorite(db, user.id, slug)
    await db.commit()
    return Response(status_code=204)
