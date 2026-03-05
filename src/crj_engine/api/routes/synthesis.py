"""Audio synthesis API — render compositions and bars to WAV."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from crj_engine.api.schemas import SynthesizeBarRequest, SynthesizeRequest
from crj_engine.synthesis.render import (
    ToneType,
    generate_tanpura,
    render_bar_audio,
    render_composition,
    save_wav,
)
from crj_engine.tala.models import Bar, Octave, SaahityaSyllable, Speed, SwaraNote
from crj_engine.tala.serializer import composition_from_dict

router = APIRouter()


def _build_bar(data: dict) -> Bar:
    """Build a Bar from API request data."""
    swaras = []
    for s in data.get("swaras", []):
        if isinstance(s, str):
            swaras.append(SwaraNote(swara_id=s))
        else:
            swaras.append(SwaraNote(
                swara_id=s.get("swara_id", "-"),
                octave=Octave(s.get("octave", "madhya")),
            ))

    sahitya = [
        SaahityaSyllable(text=t if isinstance(t, str) else t.get("text", ""))
        for t in data.get("saahitya", [""] * len(swaras))
    ]

    # Ensure saahitya matches swaras length
    while len(sahitya) < len(swaras):
        sahitya.append(SaahityaSyllable(text=""))

    speed_val = data.get("speed", 1)
    speed = Speed(speed_val) if isinstance(speed_val, int) else Speed.PRATAMA

    return Bar(
        tala_id=data.get("tala_id", "triputa_chatusra"),
        speed=speed,
        swaras=swaras,
        saahitya=sahitya,
    )


def _audio_to_wav_bytes(audio, sr: int = 44100) -> bytes:
    """Convert numpy audio array to WAV bytes in memory."""
    import numpy as np
    import soundfile as sf

    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV", subtype="FLOAT")
    buf.seek(0)
    return buf.read()


@router.post("/synthesize-bar")
async def synthesize_bar(req: SynthesizeBarRequest) -> StreamingResponse:
    """Render a single bar to WAV for preview playback."""
    bar = _build_bar(req.bar)

    tone = ToneType(req.tone) if req.tone else ToneType.VOICE

    audio = render_bar_audio(
        bar,
        reference_sa_hz=req.reference_sa_hz,
        tempo_bpm=req.tempo_bpm,
        tone=tone,
        amplitude=0.7,
    )

    wav_bytes = _audio_to_wav_bytes(audio)

    return StreamingResponse(
        io.BytesIO(wav_bytes),
        media_type="audio/wav",
        headers={"Content-Disposition": "attachment; filename=bar_preview.wav"},
    )


@router.post("/synthesize")
async def synthesize_composition(req: SynthesizeRequest) -> StreamingResponse:
    """Render a full composition to WAV."""
    comp = composition_from_dict(req.composition)

    tone = ToneType(req.tone) if req.tone else ToneType.VOICE

    audio = render_composition(
        comp,
        tempo_bpm=req.tempo_bpm,
        tone=tone,
        include_tanpura=req.include_tanpura,
        amplitude=0.7,
    )

    wav_bytes = _audio_to_wav_bytes(audio)

    return StreamingResponse(
        io.BytesIO(wav_bytes),
        media_type="audio/wav",
        headers={"Content-Disposition": "attachment; filename=composition.wav"},
    )
