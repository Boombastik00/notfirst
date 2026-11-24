from datetime import datetime

from pydantic import BaseModel


class StoryCardOut(BaseModel):
    slug: str
    title: str
    woman_name: str
    short_description: str
    story_type: str
    is_anonymous: bool
    published_at: datetime | None = None
    country: str | None = None
    profession: str | None = None


class StoryTagOut(BaseModel):
    name: str
    group: str


class StorySourceOut(BaseModel):
    title: str
    url: str | None = None
    source_type: str


class AuthorOut(BaseModel):
    id: str
    display_name: str


class StoryDetailOut(BaseModel):
    slug: str
    title: str
    woman_name: str
    short_description: str
    full_text: str
    story_type: str
    is_anonymous: bool
    published_at: datetime | None = None
    country: str | None = None
    profession: str | None = None
    age: str | None = None
    tags: list[StoryTagOut] = []
    sources: list[StorySourceOut] = []
    author: AuthorOut | None = None


class StoryListOut(BaseModel):
    items: list[StoryCardOut]
    total: int
    page: int
    pages: int
    limit: int
