"""
API Router

Главный роутер API v1.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import entries, reports, groups, trackers, users, media

api_router = APIRouter()

api_router.include_router(users.router, prefix="/me", tags=["users"])
api_router.include_router(entries.router, prefix="/entries", tags=["entries"])
api_router.include_router(reports.router, prefix="/weeks", tags=["weeks"])
api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
api_router.include_router(trackers.router, prefix="/trackers", tags=["trackers"])
api_router.include_router(media.router, prefix="/media", tags=["media"])
