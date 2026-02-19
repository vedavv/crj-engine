"""CRJ SoundScape — FastAPI application serving audio analysis API and web UI."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from crj_engine.api.routes import analyze, health, reference

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

    # Serve web UI — must come LAST so API routes take precedence
    if _WEB_DIR.exists():
        app.mount("/", StaticFiles(directory=str(_WEB_DIR), html=True), name="web")

    return app


app = create_app()
