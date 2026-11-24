from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    discovery,
    favorites,
    health,
    onboarding,
    profile,
    profiles,
    stories,
    tags,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(tags.router)
api_router.include_router(auth.router)
api_router.include_router(onboarding.router)
api_router.include_router(profile.router)
# discovery должен стоять раньше stories: иначе /stories/daily съестся как slug
api_router.include_router(discovery.router)
api_router.include_router(stories.router)
api_router.include_router(favorites.router)
api_router.include_router(profiles.router)
