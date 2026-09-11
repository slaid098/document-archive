"""Health check route (not versioned, used by load balancers)."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
async def health() -> dict[str, str]:
    return {"status": "ok"}
