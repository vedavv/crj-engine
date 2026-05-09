"""GET /api/v1/tala-loop — render a tala loop to a streamable WAV.

Also exposes GET /api/v1/tala-pattern for clients that want to do their own
client-side scheduling (e.g., for live tempo automation).
"""

from __future__ import annotations

import io

import soundfile as sf
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse

from crj_engine.synthesis.tala_engine import (
    get_pattern_dict,
    render_tala_loop,
)

router = APIRouter()

_LOOP_SR = 22050  # mono PCM_16, ~44 KB/s — keeps mobile downloads small
_INSTRUMENT_RE = "^(mridangam|pakhavaj|tabla|click)$"


@router.get("/tala-loop")
async def get_tala_loop(
    tala_id: str = Query(..., description="Tala identifier"),
    instrument: str = Query(
        "mridangam", pattern=_INSTRUMENT_RE,
        description="Percussion voice",
    ),
    tempo_bpm: float = Query(
        80.0, ge=20.0, le=320.0, description="Beats per minute (1 matra = 1 beat at 1x)",
    ),
    num_cycles: int = Query(
        4, ge=1, le=32, description="Number of full tala cycles in the rendered loop",
    ),
) -> StreamingResponse:
    """Render a tala loop to WAV. Cacheable — same params yield identical output."""
    try:
        audio = render_tala_loop(
            tala_id=tala_id,
            instrument=instrument,
            tempo_bpm=tempo_bpm,
            num_cycles=num_cycles,
            sr=_LOOP_SR,
        )
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    buf = io.BytesIO()
    sf.write(buf, audio, _LOOP_SR, format="WAV", subtype="PCM_16")
    buf.seek(0)

    filename = f"tala_{tala_id}_{instrument}_{int(tempo_bpm)}bpm.wav"
    return StreamingResponse(
        buf,
        media_type="audio/wav",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # 30-day immutable cache: same params -> identical bytes.
            "Cache-Control": "public, max-age=2592000, immutable",
        },
    )


@router.get("/tala-pattern")
async def get_tala_pattern(
    tala_id: str = Query(..., description="Tala identifier"),
    instrument: str = Query(
        "mridangam", pattern=_INSTRUMENT_RE,
    ),
) -> JSONResponse:
    """Return the stroke pattern as JSON for client-side scheduling."""
    try:
        return JSONResponse(get_pattern_dict(tala_id, instrument))
    except KeyError as e:
        raise HTTPException(404, str(e)) from e
