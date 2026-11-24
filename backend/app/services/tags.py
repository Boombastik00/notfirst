from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Tag, TagGroup


async def list_tag_groups(session: AsyncSession) -> Sequence[TagGroup]:
    result = await session.execute(select(TagGroup).order_by(TagGroup.sort_order, TagGroup.id))
    return result.scalars().all()


async def get_group_codes(session: AsyncSession) -> set[str]:
    return {group.code for group in await list_tag_groups(session)}


async def list_tags(session: AsyncSession, group_code: str | None = None) -> Sequence[Tag]:
    query = (
        select(Tag)
        .options(selectinload(Tag.group))
        .order_by(Tag.group_id, Tag.sort_order, Tag.id)
    )
    if group_code is not None:
        query = query.join(TagGroup).where(TagGroup.code == group_code)
    result = await session.execute(query)
    return result.scalars().all()
