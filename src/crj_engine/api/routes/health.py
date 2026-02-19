"""GET /api/v1/health — server health check."""

from __future__ import annotations

from fastapi import APIRouter

from crj_engine import __version__
from crj_engine.api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=__version__,
        algorithms=["crepe", "pyin"],
    )
