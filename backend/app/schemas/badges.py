from pydantic import BaseModel


class BadgeInfo(BaseModel):
    code: str
    label: str


class BadgesCatalogOut(BaseModel):
    items: list[BadgeInfo]
