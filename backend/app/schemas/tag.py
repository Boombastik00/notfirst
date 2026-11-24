from pydantic import BaseModel, ConfigDict


class TagGroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name_ru: str
    sort_order: int


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_code: str
    parent_id: int | None = None
    slug: str
    name_ru: str
    description: str | None = None
    is_active: bool
    sort_order: int
