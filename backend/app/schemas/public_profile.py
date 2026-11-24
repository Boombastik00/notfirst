
from pydantic import BaseModel


class BadgeOut(BaseModel):
    code: str
    label: str


class PublicProfileOut(BaseModel):
    id: str
    display_name: str
    avatar_url: str | None = None
    badges: list[BadgeOut] = []
    is_banned: bool = False
    # дополнительная информация видна всем только если заполнена
    current_field: str | None = None
    bio: str | None = None


class PublicStoryCard(BaseModel):
    slug: str
    title: str
    short_description: str
    story_type: str
    is_anonymous: bool
    country: str | None = None
    profession: str | None = None


class PublicStoriesOut(BaseModel):
    items: list[PublicStoryCard]
    total: int


class BadgeIn(BaseModel):
    badge: str
