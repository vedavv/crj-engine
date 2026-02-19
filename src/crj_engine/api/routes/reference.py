"""GET endpoints for reference data (swaras, ragas, tuning presets)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from crj_engine.api.schemas import SwarasthanaOut, TuningPresetOut

router = APIRouter()


@router.get("/swarasthanas", response_model=list[SwarasthanaOut])
async def get_swarasthanas(request: Request) -> list[SwarasthanaOut]:
    """Return the 12 swarasthanas with multilingual names."""
    return [
        SwarasthanaOut(
            index=s["index"],
            id=s["id"],
            cents=s["cents"],
            western_equivalent=s["western_equivalent"],
            names=s["names"],
            full_names=s["full_names"],
            is_fixed=s["is_fixed"],
            aliases=s.get("aliases", []),
        )
        for s in request.app.state.swarasthanas
    ]


@router.get("/tuning-presets", response_model=list[TuningPresetOut])
async def get_tuning_presets() -> list[TuningPresetOut]:
    """Return available Sa tuning presets."""
    from crj_engine.pitch.audio_io import load_config

    config = load_config("tuning.json")
    return [
        TuningPresetOut(
            id=pid,
            description=p["description"],
            reference_sa_hz=p["reference_sa_hz"],
            western_reference=p["western_reference"],
        )
        for pid, p in config["presets"].items()
    ]


@router.get("/ragas")
async def get_ragas(request: Request) -> list[dict]:
    """Return all 72 Melakarta ragas."""
    matcher = request.app.state.raga_matcher
    return [
        {
            "number": r.number,
            "name": r.name,
            "arohana": r.arohana,
            "avarohana": r.avarohana,
            "ma_type": r.ma_type,
            "aliases": r.aliases,
        }
        for r in matcher.ragas
    ]
