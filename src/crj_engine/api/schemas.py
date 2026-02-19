"""Pydantic models for API request/response schemas."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class PitchAlgorithmChoice(StrEnum):
    crepe = "crepe"
    pyin = "pyin"


class ScriptChoice(StrEnum):
    iast = "iast"
    devanagari = "devanagari"
    kannada = "kannada"
    tamil = "tamil"
    telugu = "telugu"


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class PitchFrameOut(BaseModel):
    timestamp_ms: float
    frequency_hz: float
    confidence: float


class TranscribedNoteOut(BaseModel):
    start_ms: float
    end_ms: float
    swara_id: str
    octave: str
    frequency_hz: float
    cents_deviation: float
    confidence: float


class TranscribedPhraseOut(BaseModel):
    notes: list[TranscribedNoteOut]
    start_ms: float
    end_ms: float


class GamakaOut(BaseModel):
    segment_start_ms: float
    segment_end_ms: float
    gamaka_type: str
    confidence: float


class RagaCandidateOut(BaseModel):
    raga_number: int
    raga_name: str
    confidence: float
    arohana: list[str]
    avarohana: list[str]


class AnalysisResponse(BaseModel):
    """Full analysis result from the /analyze endpoint."""

    status: str = "success"
    duration_s: float
    reference_sa_hz: float
    algorithm: str

    unique_swaras: list[str]
    swara_sequence: list[str]

    notation_iast: str
    notation_compact: str
    notation_requested: str
    script: str

    phrases: list[TranscribedPhraseOut]
    gamakas: list[GamakaOut]
    raga_candidates: list[RagaCandidateOut]

    pitch_contour: list[PitchFrameOut] | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    algorithms: list[str]


class TuningPresetOut(BaseModel):
    id: str
    description: str
    reference_sa_hz: float
    western_reference: str


class SwarasthanaOut(BaseModel):
    index: int
    id: str
    cents: float
    western_equivalent: str
    names: dict[str, str]
    full_names: dict[str, str]
    is_fixed: bool
    aliases: list[str]
