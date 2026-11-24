from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserConsent

# единая точка фиксации согласий: какое кем и когда принято
CONSENT_VERSION = "2026-11-24"

KIND_TERMS = "terms"
KIND_PD = "pd_processing"
KIND_PARENTAL = "parental"
KIND_PUBLICATION = "publication"


async def record(
    db: AsyncSession, user_id, kind: str, version: str = CONSENT_VERSION, note: str | None = None
) -> None:
    db.add(UserConsent(user_id=user_id, kind=kind, version=version, note=note))
