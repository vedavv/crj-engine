"""Audio-to-notation transcription — convert pitch analysis into swara notation.

Takes a pitch contour from audio analysis and produces a readable notation
with octave marks, grouped into time-based phrases. Supports both Carnatic
tala-aligned notation and free-form (e.g. Vedic chanting) transcription.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from crj_engine.pitch.detector import PitchContour
from crj_engine.swara.mapper import SwaraMatch, freq_to_swara
from crj_engine.tala.models import Octave, SwaraNote
from crj_engine.tala.notation import render_swara

# Unicode box-drawing and markers
_BAR_LINE = "|"
_DOT_BELOW = "\u0323"
_DOT_ABOVE = "\u0307"


@dataclass
class TranscribedNote:
    """A single transcribed note with timing and swara info."""

    start_ms: float
    end_ms: float
    swara_id: str
    octave: Octave
    frequency_hz: float
    cents_deviation: float
    confidence: float

    @property
    def duration_ms(self) -> float:
        return self.end_ms - self.start_ms

    def to_swara_note(self) -> SwaraNote:
        return SwaraNote(swara_id=self.swara_id, octave=self.octave)


@dataclass
class TranscribedPhrase:
    """A group of consecutive notes forming a phrase."""

    notes: list[TranscribedNote]
    start_ms: float = 0.0
    end_ms: float = 0.0

    def __post_init__(self):
        if self.notes:
            self.start_ms = self.notes[0].start_ms
            self.end_ms = self.notes[-1].end_ms


@dataclass
class Transcription:
    """Complete transcription of an audio recording."""

    phrases: list[TranscribedPhrase]
    reference_sa_hz: float
    duration_s: float
    unique_swaras: list[str] = field(default_factory=list)


def _freq_to_octave(freq_hz: float, reference_sa_hz: float) -> Octave:
    """Determine the octave register of a frequency relative to Sa."""
    if freq_hz <= 0 or reference_sa_hz <= 0:
        return Octave.MADHYA
    cents = 1200 * math.log2(freq_hz / reference_sa_hz)
    if cents < -300:
        return Octave.MANDRA
    elif cents > 900:
        return Octave.TARA
    return Octave.MADHYA


def transcribe_contour(
    contour: PitchContour,
    reference_sa_hz: float = 261.63,
    tolerance_cents: float = 40.0,
    min_confidence: float = 0.3,
    min_note_ms: float = 80.0,
    phrase_gap_ms: float = 300.0,
) -> Transcription:
    """Transcribe a pitch contour into swara notation.

    Groups consecutive frames of the same swara into notes, then groups
    notes into phrases separated by silences.

    Args:
        contour: PitchContour from pitch detection.
        reference_sa_hz: Tonic Sa frequency in Hz.
        tolerance_cents: Maximum cents deviation for swara matching.
        min_confidence: Minimum voiced confidence threshold.
        min_note_ms: Minimum note duration in ms (filters transients).
        phrase_gap_ms: Silence gap (ms) that separates phrases.

    Returns:
        A Transcription with phrases containing transcribed notes.
    """
    hop_ms = contour.hop_ms

    # Step 1: Map each frame to a swara
    frame_swaras: list[tuple[float, SwaraMatch | None, float]] = []
    for frame in contour.frames:
        if frame.frequency_hz <= 0 or frame.confidence < min_confidence:
            frame_swaras.append((frame.timestamp_ms, None, frame.confidence))
        else:
            match = freq_to_swara(
                frame.frequency_hz,
                reference_sa_hz=reference_sa_hz,
                tolerance_cents=tolerance_cents,
            )
            frame_swaras.append((frame.timestamp_ms, match, frame.confidence))

    # Step 2: Run-length encode into note segments
    raw_notes: list[TranscribedNote] = []
    i = 0
    while i < len(frame_swaras):
        ts, match, conf = frame_swaras[i]
        if match is None:
            i += 1
            continue

        # Start a new note run
        swara_id = match.swara_id
        octave = _freq_to_octave(match.frequency_hz, reference_sa_hz)
        start_ms = ts
        freqs = [match.frequency_hz]
        devs = [match.cents_deviation]
        confs = [conf]

        j = i + 1
        while j < len(frame_swaras):
            ts_j, match_j, conf_j = frame_swaras[j]
            if match_j is None or match_j.swara_id != swara_id:
                break
            freqs.append(match_j.frequency_hz)
            devs.append(match_j.cents_deviation)
            confs.append(conf_j)
            j += 1

        end_ms = frame_swaras[j - 1][0] + hop_ms
        duration = end_ms - start_ms

        if duration >= min_note_ms:
            raw_notes.append(TranscribedNote(
                start_ms=start_ms,
                end_ms=end_ms,
                swara_id=swara_id,
                octave=octave,
                frequency_hz=float(np.mean(freqs)),
                cents_deviation=float(np.mean(devs)),
                confidence=float(np.mean(confs)),
            ))

        i = j

    # Step 3: Group notes into phrases (separated by gaps)
    phrases: list[TranscribedPhrase] = []
    if raw_notes:
        current_phrase: list[TranscribedNote] = [raw_notes[0]]
        for note in raw_notes[1:]:
            gap = note.start_ms - current_phrase[-1].end_ms
            if gap > phrase_gap_ms:
                phrases.append(TranscribedPhrase(notes=current_phrase))
                current_phrase = [note]
            else:
                current_phrase.append(note)
        phrases.append(TranscribedPhrase(notes=current_phrase))

    # Unique swaras
    all_ids = sorted({n.swara_id for p in phrases for n in p.notes})

    duration_s = contour.frames[-1].timestamp_ms / 1000 if contour.frames else 0

    return Transcription(
        phrases=phrases,
        reference_sa_hz=reference_sa_hz,
        duration_s=duration_s,
        unique_swaras=all_ids,
    )


# ---------------------------------------------------------------------------
# Notation rendering
# ---------------------------------------------------------------------------

def render_transcription(
    transcription: Transcription,
    script: str = "iast",
    notes_per_line: int = 8,
    show_timing: bool = True,
) -> str:
    """Render a transcription as readable notation text.

    Args:
        transcription: The Transcription to render.
        script: Display script ("iast", "devanagari", "kannada", "tamil", "telugu").
        notes_per_line: How many notes per line before wrapping.
        show_timing: Whether to show timestamps.

    Returns:
        Multi-line formatted notation string.
    """
    lines: list[str] = []

    for pi, phrase in enumerate(transcription.phrases):
        if show_timing:
            t_start = phrase.start_ms / 1000
            t_end = phrase.end_ms / 1000
            lines.append(f"  Phrase {pi + 1}  [{t_start:.1f}s – {t_end:.1f}s]")
        else:
            lines.append(f"  Phrase {pi + 1}")

        # Render notes in rows of notes_per_line
        note_strs: list[str] = []
        for note in phrase.notes:
            sn = note.to_swara_note()
            rendered = render_swara(sn, script=script)
            # Indicate sustain with duration markers
            beats = max(1, round(note.duration_ms / 250))
            if beats > 1:
                rendered += " " + ",  " * (beats - 1)
            note_strs.append(rendered.strip())

        # Group into lines
        for i in range(0, len(note_strs), notes_per_line):
            chunk = note_strs[i : i + notes_per_line]
            bar_mid = len(chunk) // 2
            if len(chunk) > 4:
                first_half = "  ".join(chunk[:bar_mid])
                second_half = "  ".join(chunk[bar_mid:])
                lines.append(f"    {first_half}  {_BAR_LINE}  {second_half}")
            else:
                lines.append(f"    {'  '.join(chunk)}")

        lines.append("")

    return "\n".join(lines)


def render_transcription_compact(
    transcription: Transcription,
    script: str = "iast",
) -> str:
    """Render a compact single-line notation per phrase.

    Uses commas for sustain and dashes for gaps between phrases.
    """
    parts: list[str] = []

    for phrase in transcription.phrases:
        phrase_notes: list[str] = []
        for note in phrase.notes:
            sn = note.to_swara_note()
            rendered = render_swara(sn, script=script)
            beats = max(1, round(note.duration_ms / 250))
            phrase_notes.append(rendered)
            for _ in range(beats - 1):
                phrase_notes.append(",")
        parts.append(" ".join(phrase_notes))

    return "  ||  ".join(parts)
