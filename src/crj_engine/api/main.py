"""CRJ SoundScape — FastAPI application serving audio analysis API and web UI."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from crj_engine.api.routes import (
    analyze,
    compose,
    compositions,
    detect_sa,
    export,
    health,
    reference,
    shruti,
    synthesis,
    talas,
)

_WEB_DIR = Path(__file__).resolve().parents[3] / "web"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-load heavy resources on startup."""
    from crj_engine.raga.matcher import RagaMatcher
    from crj_engine.swara.mapper import _load_swarasthanas

    app.state.raga_matcher = RagaMatcher()
    app.state.swarasthanas = _load_swarasthanas()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="CRJ SoundScape",
        description="Audio analysis API for Indian classical music",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(analyze.router, prefix="/api/v1", tags=["analyze"])
    app.include_router(reference.router, prefix="/api/v1", tags=["reference"])
    app.include_router(talas.router, prefix="/api/v1", tags=["talas"])
    app.include_router(compositions.router, prefix="/api/v1", tags=["compositions"])
    app.include_router(synthesis.router, prefix="/api/v1", tags=["synthesis"])
    app.include_router(compose.router, prefix="/api/v1", tags=["compose"])
    app.include_router(export.router, prefix="/api/v1", tags=["export"])
    app.include_router(shruti.router, prefix="/api/v1", tags=["shruti"])
    app.include_router(detect_sa.router, prefix="/api/v1", tags=["detect-sa"])

    # Serve web UI — must come LAST so API routes take precedence
    if _WEB_DIR.exists():
        app.mount("/", StaticFiles(directory=str(_WEB_DIR), html=True), name="web")

    return app


app = create_app()
