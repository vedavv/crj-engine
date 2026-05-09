"""POST /api/v1/detect-sa — suggest the tonic Sa frequency for an audio clip."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from crj_engine.api.schemas import TonicCandidateOut, TonicDetectionResponse

router = APIRouter()

_MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024
_MAX_DURATION_S = 60.0  # Sa detection only needs a short window
_ALLOWED_EXTENSIONS = {
    ".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac", ".webm",
}


@router.post("/detect-sa", response_model=TonicDetectionResponse)
async def detect_sa(
    file: UploadFile = File(..., description="Short vocal/melody clip"),
) -> TonicDetectionResponse:
    """Suggest the most likely Sa frequency for an uploaded audio clip.

    Uses pitch-class histogram analysis with Sa-Pa relationship validation.
    Works best on solo vocal recordings (with or without a drone) of 5-30 s.
    """
    from crj_engine.pitch.audio_io import get_duration, load_audio
    from crj_engine.pitch.tonic import detect_tonic

    content = await file.read()
    if len(content) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(413, "File too large")

    filename = file.filename or "clip.wav"
    suffix = Path(filename).suffix.lower() or ".wav"
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported format: {suffix}")

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        audio, sr = load_audio(tmp_path, target_sr=16000)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    duration_s = get_duration(audio, sr)
    if duration_s < 1.0:
        raise HTTPException(400, "Clip too short for tonic detection (< 1s)")
    if duration_s > _MAX_DURATION_S:
        # Trim to first 60s — extra audio would slow detection without
        # meaningfully improving accuracy.
        audio = audio[: int(_MAX_DURATION_S * sr)]

    result = detect_tonic(audio, sr=sr)

    return TonicDetectionResponse(
        suggested_sa_hz=result.suggested_sa_hz,
        western_label=result.western_label,
        confidence=result.confidence,
        candidates=[
            TonicCandidateOut(
                sa_hz=c.sa_hz,
                western_label=c.western_label,
                confidence=c.confidence,
                has_perfect_fifth=c.has_perfect_fifth,
            )
            for c in result.candidates
        ],
        voiced_frame_count=result.voiced_frame_count,
    )
