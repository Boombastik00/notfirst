from datetime import datetime

from pydantic import BaseModel


class MyStoryCardOut(BaseModel):
    slug: str
    title: str
    short_description: str
    story_type: str
    verification_status: str
    publication_status: str
    created_at: datetime
    country: str | None = None
    profession: str | None = None


class MyStoriesOut(BaseModel):
    items: list[MyStoryCardOut]
    total: int
