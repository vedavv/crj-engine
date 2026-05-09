"""GET /api/v1/shruti — render a Shruti (tanpura) loop at chosen Sa + pattern."""

from __future__ import annotations

import io

import soundfile as sf
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from crj_engine.synthesis.render import _SHRUTI_PATTERN_CENTS, generate_tanpura

router = APIRouter()

# 20s loop covers 3 breathing cycles (~6.67s each) and loops seamlessly
_DEFAULT_DURATION_S = 20.0
_LOOP_SR = 22050  # Mono, 16-bit at this rate -> ~860 KB for 20s WAV


@router.get("/shruti")
async def get_shruti(
    sa_hz: float = Query(261.63, ge=50.0, le=1000.0, description="Sa frequency"),
    pattern: str = Query(
        "sa_pa",
        pattern="^(sa_pa|sa_ma|sa_ni)$",
        description="Pluck pattern: sa_pa | sa_ma | sa_ni",
    ),
    duration_s: float = Query(
        _DEFAULT_DURATION_S, ge=5.0, le=60.0, description="Loop length in seconds"
    ),
) -> StreamingResponse:
    """Render a Shruti (tanpura drone) WAV loop for client-side looping playback.

    Returned WAV is 22.05 kHz mono PCM_16, sized to be seamlessly loopable
    (duration is a multiple of the breathing modulation period).
    """
    if pattern not in _SHRUTI_PATTERN_CENTS:
        raise HTTPException(400, f"Unknown pattern: {pattern}")

    audio = generate_tanpura(
        reference_sa_hz=sa_hz,
        duration_s=duration_s,
        sr=_LOOP_SR,
        pattern=pattern,
    )

    buf = io.BytesIO()
    sf.write(buf, audio, _LOOP_SR, format="WAV", subtype="PCM_16")
    buf.seek(0)

    filename = f"shruti_{pattern}_{int(round(sa_hz * 100))}.wav"
    return StreamingResponse(
        buf,
        media_type="audio/wav",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # 30-day cache — same Sa+pattern always produces identical output
            "Cache-Control": "public, max-age=2592000, immutable",
        },
    )
