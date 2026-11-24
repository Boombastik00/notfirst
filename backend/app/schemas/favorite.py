from datetime import datetime

from pydantic import BaseModel


class FavoriteCardOut(BaseModel):
    slug: str
    title: str
    woman_name: str
    short_description: str
    story_type: str
    is_anonymous: bool
    published_at: datetime | None = None
    country: str | None = None
    profession: str | None = None


class FavoriteListOut(BaseModel):
    items: list[FavoriteCardOut]
    total: int
