"""API v1 router."""

from fastapi import APIRouter

from app.api.v1.documents import router as documents_router
from app.api.v1.stats import router as stats_router

router = APIRouter()
router.include_router(documents_router)
router.include_router(stats_router)
