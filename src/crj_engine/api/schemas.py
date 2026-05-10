"""Pydantic models for API request/response schemas."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


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


class SeparatorEventOut(BaseModel):
    event_type: str
    start_ms: float
    end_ms: float
    confidence: float


class SRTUnitOut(BaseModel):
    index: int
    text: str
    start_ms: float
    end_ms: float
    source: str


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
    separator_events: list[SeparatorEventOut] = Field(default_factory=list)
    srt_units: list[SRTUnitOut] = Field(default_factory=list)


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


# ---------------------------------------------------------------------------
# Composition models
# ---------------------------------------------------------------------------


class SwaraIn(BaseModel):
    swara_id: str
    octave: str = "madhya"


class BarIn(BaseModel):
    tala_id: str
    speed: int = 1
    swaras: list[SwaraIn | str]
    saahitya: list[str] = []


class LineIn(BaseModel):
    bars: list[BarIn]
    repeat: int = 2


class SectionIn(BaseModel):
    name: str
    lines: list[LineIn]


class CompositionIn(BaseModel):
    """Input schema for creating/updating a composition."""

    title: str
    raga: str
    tala_id: str
    composer: str = ""
    reference_sa_hz: float = 261.63
    sections: list[SectionIn] = []


class CompositionOut(BaseModel):
    """Output schema for a composition."""

    id: str
    title: str
    raga: str
    tala_id: str
    composer: str = ""
    reference_sa_hz: float = 261.63
    sections: list[SectionIn] = []


# ---------------------------------------------------------------------------
# Synthesis request models
# ---------------------------------------------------------------------------


class SynthesizeBarRequest(BaseModel):
    """Request to render a single bar to WAV."""

    bar: dict
    reference_sa_hz: float = 261.63
    tempo_bpm: float = 60.0
    tone: str = "voice"


class SynthesizeRequest(BaseModel):
    """Request to render a full composition to WAV."""

    composition: dict
    tempo_bpm: float = 60.0
    tone: str = "voice"
    include_tanpura: bool = True


# ---------------------------------------------------------------------------
# Compose (text notation → audio) request model
# ---------------------------------------------------------------------------


class ToneChoice(StrEnum):
    voice = "voice"
    string = "string"
    flute = "flute"
    sine = "sine"


class ComposeRequest(BaseModel):
    """Request to synthesize audio from text notation."""

    notation: str
    reference_sa_hz: float = 261.63
    tone: ToneChoice = ToneChoice.voice
    tempo_bpm: float = 60.0
    speed: int = 1
    tala_id: str | None = None
    include_tanpura: bool = False
    include_click_track: bool = False


# ---------------------------------------------------------------------------
# Sa (tonic) auto-detection
# ---------------------------------------------------------------------------


class TonicCandidateOut(BaseModel):
    sa_hz: float
    western_label: str
    confidence: float
    has_perfect_fifth: bool


class TonicDetectionResponse(BaseModel):
    suggested_sa_hz: float
    western_label: str
    confidence: float
    candidates: list[TonicCandidateOut]
    voiced_frame_count: int
