"""POST /api/v1/compose — synthesize a WAV from text swara notation."""

from __future__ import annotations

import io

import numpy as np
import soundfile as sf
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from crj_engine.api.schemas import ComposeRequest
from crj_engine.synthesis.render import (
    ToneType,
    generate_tanpura,
    render_bar_audio,
)
from crj_engine.tala.models import (
    Bar,
    Octave,
    SaahityaSyllable,
    Speed,
    SwaraNote,
    get_tala,
)

router = APIRouter()

_DEFAULT_TALA_ID = "adi"
_SAMPLE_RATE = 44100


def _parse_notation(notation: str) -> list[SwaraNote]:
    """Split a notation string into SwaraNotes.

    Token conventions:
      Sa, Ri1, Ri2, Ga3, Ma1, Pa, Dha2, Ni3 — madhya (default)
      Sa. / Sa,. — mandra (lower octave)
      Sa' / Sa^ — tara (upper octave)
      "-" — rest    "," — sustain previous note
    """
    swaras: list[SwaraNote] = []
    for raw in notation.split():
        token = raw.strip()
        if not token:
            continue

        octave = Octave.MADHYA
        if token.endswith("'") or token.endswith("^"):
            octave = Octave.TARA
            token = token[:-1]
        elif token.endswith(".") and len(token) > 1:
            octave = Octave.MANDRA
            token = token[:-1]

        if token in {"-", ","}:
            swaras.append(SwaraNote(swara_id=token))
        else:
            swaras.append(SwaraNote(swara_id=token, octave=octave))
    return swaras


def _generate_click_track(
    *,
    duration_s: float,
    tempo_bpm: float,
    beats_per_cycle: int,
    sr: int,
) -> np.ndarray:
    """Simple metronome click — accented sam, lighter on remaining beats."""
    n = int(sr * duration_s)
    audio = np.zeros(n, dtype=np.float32)
    seconds_per_beat = 60.0 / tempo_bpm
    click_duration_s = 0.030
    click_samples = int(sr * click_duration_s)

    beat_idx = 0
    t = 0.0
    while t < duration_s:
        sample_idx = int(t * sr)
        if sample_idx + click_samples > n:
            break
        is_sam = beat_idx % beats_per_cycle == 0
        freq = 1200.0 if is_sam else 800.0
        amp = 0.55 if is_sam else 0.30
        ts = np.linspace(0, click_duration_s, click_samples, endpoint=False)
        click = amp * np.sin(2 * np.pi * freq * ts)
        # Exponential decay so the click sounds percussive
        click *= np.exp(-np.linspace(0, 6.0, click_samples))
        audio[sample_idx : sample_idx + click_samples] += click.astype(np.float32)

        t += seconds_per_beat
        beat_idx += 1
    return audio


def _normalize(audio: np.ndarray, headroom: float = 0.95) -> np.ndarray:
    peak = float(np.max(np.abs(audio)))
    if peak > headroom:
        return (audio / peak * headroom).astype(np.float32)
    return audio


@router.post("/compose")
async def compose(req: ComposeRequest) -> StreamingResponse:
    """Render a swara notation string to WAV with optional tanpura + click."""
    swaras = _parse_notation(req.notation)
    if not swaras:
        raise HTTPException(400, "Empty or invalid notation")

    saahitya = [SaahityaSyllable(text="") for _ in swaras]
    speed = Speed(req.speed) if req.speed in (1, 2, 3) else Speed.PRATAMA

    if req.tala_id:
        try:
            get_tala(req.tala_id)
        except KeyError as e:
            raise HTTPException(400, f"Unknown tala: {req.tala_id}") from e
        bar_tala_id = req.tala_id
    else:
        bar_tala_id = _DEFAULT_TALA_ID

    bar = Bar(
        tala_id=bar_tala_id,
        speed=speed,
        swaras=swaras,
        saahitya=saahitya,
    )

    tone_value = req.tone.value if hasattr(req.tone, "value") else str(req.tone)
    tone = ToneType(tone_value)

    audio = render_bar_audio(
        bar,
        reference_sa_hz=req.reference_sa_hz,
        tempo_bpm=req.tempo_bpm,
        tone=tone,
        amplitude=0.7,
    )
    duration_s = len(audio) / _SAMPLE_RATE

    if req.include_tanpura:
        tanpura = generate_tanpura(
            req.reference_sa_hz,
            duration_s,
            sr=_SAMPLE_RATE,
        )
        if len(tanpura) > len(audio):
            tanpura = tanpura[: len(audio)]
        elif len(tanpura) < len(audio):
            tanpura = np.pad(tanpura, (0, len(audio) - len(tanpura)))
        audio = audio + tanpura.astype(np.float32) * 0.15

    if req.include_click_track:
        beats_per_cycle = (
            get_tala(req.tala_id).total_aksharas if req.tala_id else 8
        )
        clicks = _generate_click_track(
            duration_s=duration_s,
            tempo_bpm=req.tempo_bpm,
            beats_per_cycle=beats_per_cycle,
            sr=_SAMPLE_RATE,
        )
        if len(clicks) > len(audio):
            clicks = clicks[: len(audio)]
        elif len(clicks) < len(audio):
            clicks = np.pad(clicks, (0, len(audio) - len(clicks)))
        audio = audio + clicks * 0.4

    audio = _normalize(audio)

    buf = io.BytesIO()
    sf.write(buf, audio, _SAMPLE_RATE, format="WAV", subtype="FLOAT")
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="audio/wav",
        headers={"Content-Disposition": "attachment; filename=composition.wav"},
    )
