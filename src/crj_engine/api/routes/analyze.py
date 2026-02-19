"""POST /api/v1/analyze — upload audio, run full analysis pipeline, return results."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from crj_engine.api.schemas import (
    AnalysisResponse,
    GamakaOut,
    PitchAlgorithmChoice,
    PitchFrameOut,
    RagaCandidateOut,
    ScriptChoice,
    TranscribedNoteOut,
    TranscribedPhraseOut,
)

router = APIRouter()

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_DURATION_S = 30.0  # Phase 1 limit (bump to 120 later)
ALLOWED_EXTENSIONS = {
    ".wav", ".mp3", ".m4a", ".aac", ".ogg", ".flac", ".webm",
}


def _validate_upload(file: UploadFile, content: bytes) -> str:
    """Validate file size and extension. Return the file suffix."""
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            413,
            f"File too large ({len(content)} bytes). Maximum: {MAX_FILE_SIZE_BYTES}.",
        )

    filename = file.filename or "recording.webm"
    suffix = Path(filename).suffix.lower()
    if not suffix:
        suffix = ".webm"

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported format: {suffix}. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    return suffix


_FILE_PARAM = File(..., description="Audio file (WAV, MP3, M4A, WebM)")
_SA_PARAM = Form(261.63, description="Tonic Sa frequency in Hz")
_ALGO_PARAM = Form(PitchAlgorithmChoice.pyin, description="Pitch detection algorithm")
_SCRIPT_PARAM = Form(ScriptChoice.iast, description="Notation script")
_CONTOUR_PARAM = Form(False, description="Include raw pitch contour")
_TOL_PARAM = Form(40.0, description="Swara matching tolerance")


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_audio(
    request: Request,
    file: UploadFile = _FILE_PARAM,
    reference_sa_hz: float = _SA_PARAM,
    algorithm: PitchAlgorithmChoice = _ALGO_PARAM,
    script: ScriptChoice = _SCRIPT_PARAM,
    include_contour: bool = _CONTOUR_PARAM,
    tolerance_cents: float = _TOL_PARAM,
) -> AnalysisResponse:
    """Run the full CRJ Engine analysis pipeline on uploaded audio.

    Pipeline: load audio -> detect pitch -> transcribe swaras ->
    classify gamakas -> identify raga -> render notation.
    """
    from crj_engine.pitch.audio_io import get_duration, load_audio
    from crj_engine.pitch.detector import PitchAlgorithm, detect_pitch
    from crj_engine.pitch.gamaka import classify_gamaka
    from crj_engine.pitch.segmenter import segment_contour
    from crj_engine.tala.transcribe import (
        render_transcription,
        render_transcription_compact,
        transcribe_contour,
    )

    # --- 1. Read and validate upload ---
    content = await file.read()
    suffix = _validate_upload(file, content)

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        audio, sr = load_audio(tmp_path, target_sr=16000)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    duration_s = get_duration(audio, sr)
    if duration_s > MAX_DURATION_S:
        raise HTTPException(
            400,
            f"Audio too long ({duration_s:.1f}s). Maximum: {MAX_DURATION_S}s.",
        )
    if duration_s < 0.5:
        raise HTTPException(400, "Audio too short (< 0.5s).")

    # --- 2. Pitch detection ---
    algo = (
        PitchAlgorithm.CREPE
        if algorithm == PitchAlgorithmChoice.crepe
        else PitchAlgorithm.PYIN
    )
    contour = detect_pitch(audio, sr, algorithm=algo)

    # --- 3. Transcribe to notation ---
    transcription = transcribe_contour(
        contour,
        reference_sa_hz=reference_sa_hz,
        tolerance_cents=tolerance_cents,
        min_confidence=0.3,
    )

    # --- 4. Gamaka classification ---
    segments = segment_contour(
        contour,
        window_ms=300.0,
        hop_ms=100.0,
        reference_sa_hz=reference_sa_hz,
    )
    gamakas = []
    for seg in segments:
        g = classify_gamaka(seg, hop_ms=contour.hop_ms)
        gamakas.append(GamakaOut(
            segment_start_ms=seg.start_ms,
            segment_end_ms=seg.end_ms,
            gamaka_type=g.gamaka_type,
            confidence=g.confidence,
        ))

    # --- 5. Build swara sequence and identify raga ---
    swara_sequence: list[str] = []
    for phrase in transcription.phrases:
        for note in phrase.notes:
            if not swara_sequence or note.swara_id != swara_sequence[-1]:
                swara_sequence.append(note.swara_id)

    matcher = request.app.state.raga_matcher
    candidates_raw = matcher.identify(swara_sequence, top_n=5)
    raga_candidates = [
        RagaCandidateOut(
            raga_number=c.raga.number,
            raga_name=c.raga.name,
            confidence=c.confidence,
            arohana=c.raga.arohana,
            avarohana=c.raga.avarohana,
        )
        for c in candidates_raw
    ]

    # --- 6. Render notation ---
    notation_iast = render_transcription(transcription, script="iast")
    notation_compact = render_transcription_compact(transcription, script="iast")
    notation_requested = render_transcription(transcription, script=script.value)

    # --- 7. Build phrase output ---
    phrases_out = [
        TranscribedPhraseOut(
            notes=[
                TranscribedNoteOut(
                    start_ms=n.start_ms,
                    end_ms=n.end_ms,
                    swara_id=n.swara_id,
                    octave=n.octave.value,
                    frequency_hz=round(n.frequency_hz, 2),
                    cents_deviation=round(n.cents_deviation, 2),
                    confidence=round(n.confidence, 3),
                )
                for n in phrase.notes
            ],
            start_ms=phrase.start_ms,
            end_ms=phrase.end_ms,
        )
        for phrase in transcription.phrases
    ]

    # --- 8. Optional pitch contour ---
    contour_out = None
    if include_contour:
        contour_out = [
            PitchFrameOut(
                timestamp_ms=f.timestamp_ms,
                frequency_hz=round(f.frequency_hz, 2),
                confidence=round(f.confidence, 3),
            )
            for f in contour.frames
        ]

    return AnalysisResponse(
        duration_s=round(duration_s, 2),
        reference_sa_hz=reference_sa_hz,
        algorithm=algo.value,
        unique_swaras=transcription.unique_swaras,
        swara_sequence=swara_sequence,
        notation_iast=notation_iast,
        notation_compact=notation_compact,
        notation_requested=notation_requested,
        script=script.value,
        phrases=phrases_out,
        gamakas=gamakas,
        raga_candidates=raga_candidates,
        pitch_contour=contour_out,
    )
