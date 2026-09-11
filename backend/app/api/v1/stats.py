"""Archive stats route (v1)."""

from fastapi import APIRouter

from app.schemas.stats import ArchiveStats
from app.services import stats as stats_service

router = APIRouter(tags=["stats"])


@router.get("/stats", summary="Archive volume and saved space")
async def get_stats() -> ArchiveStats:
    return await stats_service.archive_stats()
