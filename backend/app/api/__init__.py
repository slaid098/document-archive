"""API router aggregation. Owns the URL layout: /health at root, versioned API under /api/v1."""

from fastapi import APIRouter

from app.api import v1
from app.api.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(v1.router, prefix="/api/v1")

__all__ = ["api_router"]
