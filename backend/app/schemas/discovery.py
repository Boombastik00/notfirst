from datetime import datetime

from pydantic import BaseModel, Field


class StoryCardFull(BaseModel):
    slug: str
    title: str
    woman_name: str
    short_description: str
    full_text: str
    story_type: str
    is_anonymous: bool
    country: str | None = None
    profession: str | None = None


class MatchReason(BaseModel):
    dimension: str
    text: str
    tag: str | None = None


class FeedItem(BaseModel):
    story: StoryCardFull
    match_reasons: list[MatchReason] = []
    random: bool = False


class RecommendationOut(BaseModel):
    story: StoryCardFull | None = None
    match_reasons: list[MatchReason] = []
    random: bool = False
    feed: list[FeedItem] = []


class DailyOut(BaseModel):
    story: StoryCardFull


class SubmitStoryIn(BaseModel):
    text: str = Field(min_length=1, max_length=15000)
    title: str | None = Field(default=None, max_length=200)
    field_tag_id: int | None = None
    profession_tag_id: int | None = None
    obstacle_tag_id: int | None = None
    # согласие на публикацию и распространение сведений из истории, без него не публикуем
    consent_publication: bool = False


class OfficialSourceIn(BaseModel):
    title: str = Field(max_length=300)
    url: str | None = Field(default=None, max_length=1000)


class SubmitOfficialIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=200, max_length=50000)
    sources: list[OfficialSourceIn] = Field(default_factory=list)


class PendingStoryOut(BaseModel):
    id: str
    slug: str
    title: str
    text: str
    created_by: str | None = None
    created_at: datetime
    story_type: str = "community_story"
    sources: list[dict] = []
