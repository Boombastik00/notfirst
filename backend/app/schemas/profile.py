from pydantic import BaseModel, Field

from app.schemas.tag import TagOut


class OnboardingOptionsOut(BaseModel):
    age_categories: list[TagOut]
    countries: list[TagOut]
    professions: list[TagOut]
    fields: list[TagOut]
    themes: list[TagOut]


class OnboardingCurrentOut(BaseModel):
    age_tag_id: int | None = None
    country_tag_id: int | None = None
    profession_tag_id: int | None = None
    current_field_tag_id: int | None = None
    interest_tag_ids: list[int] = []


class OnboardingOut(BaseModel):
    already_completed: bool
    options: OnboardingOptionsOut
    current: OnboardingCurrentOut


class OnboardingIn(BaseModel):
    # пропуск засчитываем как завершение флоу, анкету можно заполнить в профиле позже
    skip: bool = False
    age_tag_id: int | None = None
    country_tag_id: int | None = None
    profession_tag_id: int | None = None
    current_field_tag_id: int | None = None
    interest_tag_ids: list[int] = Field(default_factory=list)
    # для младше 14: подтверждение согласия законного представителя
    parent_confirmed: bool = False


class ProfileOut(BaseModel):
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    age: TagOut | None = None
    country: TagOut | None = None
    profession: TagOut | None = None
    current_field: TagOut | None = None
    interests: list[TagOut] = []
    onboarding_completed: bool = False


class ProfileUpdateIn(BaseModel):
    display_name: str | None = None
    bio: str | None = Field(default=None, max_length=1000)
    age_tag_id: int | None = None
    country_tag_id: int | None = None
    profession_tag_id: int | None = None
    current_field_tag_id: int | None = None


class InterestsUpdateIn(BaseModel):
    tag_ids: list[int] = Field(default_factory=list)
