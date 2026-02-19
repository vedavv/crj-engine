"""Tala (rhythm) composition and notation module.

Provides data structures for composing Carnatic music with:
- 35 Suladi Sapta Tala definitions
- Swara notation with octave marks (mandra/madhya/tara)
- Saahitya (lyrics) alignment
- Speed variations (pratama/dvitiya/tritiya kala)
- Composition serialization (save/load as JSON)
"""

from crj_engine.tala.models import (
    Bar,
    Composition,
    Jati,
    Line,
    Octave,
    SaahityaSyllable,
    Section,
    Speed,
    SwaraNote,
    TalaDefinition,
    get_tala,
    load_tala_db,
)
from crj_engine.tala.notation import (
    render_bar,
    render_bar_saahitya,
    render_bar_swaras,
    render_swara,
)
from crj_engine.tala.serializer import (
    load_composition,
    save_composition,
)
from crj_engine.tala.transcribe import (
    Transcription,
    render_transcription,
    render_transcription_compact,
    transcribe_contour,
)

__all__ = [
    "Bar",
    "Composition",
    "Jati",
    "Line",
    "Octave",
    "SaahityaSyllable",
    "Section",
    "Speed",
    "SwaraNote",
    "TalaDefinition",
    "Transcription",
    "get_tala",
    "load_tala_db",
    "load_composition",
    "render_bar",
    "render_bar_saahitya",
    "render_bar_swaras",
    "render_swara",
    "render_transcription",
    "render_transcription_compact",
    "save_composition",
    "transcribe_contour",
]
