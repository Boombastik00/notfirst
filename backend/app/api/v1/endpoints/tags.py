from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.tag import TagGroupOut, TagOut
from app.services import tags as tag_service

router = APIRouter(tags=["tags"])


@router.get("/tag-groups", response_model=list[TagGroupOut])
async def get_tag_groups(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TagGroupOut]:
    groups = await tag_service.list_tag_groups(db)
    return [TagGroupOut.model_validate(group) for group in groups]


@router.get("/tags", response_model=list[TagOut])
async def get_tags(
    db: Annotated[AsyncSession, Depends(get_db)],
    group: Annotated[str | None, Query(description="код группы тегов")] = None,
) -> list[TagOut]:
    if group is not None and group not in await tag_service.get_group_codes(db):
        raise HTTPException(status_code=404, detail="группа тегов не найдена")
    items = await tag_service.list_tags(db, group)
    return [TagOut.model_validate(item) for item in items]
