"""Tala engine — render a tala loop as a single audio buffer.

Inputs:
  - tala_id (must exist in load_tala_db)
  - instrument (mridangam | pakhavaj | tabla | click)
  - tempo_bpm
  - num_cycles

Output: a numpy float32 audio array at the given sample rate, ready for WAV
encoding. Strokes are scheduled at one-stroke-per-matra (speed 1x). The
client controls tempo by re-requesting a new render — patterns and strokes
are fast to synthesise (lru_cached), so even tempo-slider drags stay snappy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from crj_engine.synthesis.percussion import synthesize_stroke
from crj_engine.tala.models import load_tala_db

_CONFIGS_DIR = Path(__file__).resolve().parents[3] / "configs"
_PATTERN_PATH = _CONFIGS_DIR / "talas" / "stroke_patterns.json"

_PATTERN_CACHE: dict[tuple[str, str], "StrokePattern"] | None = None

_DEFAULT_SR = 44100
_AVAILABLE_INSTRUMENTS = ("mridangam", "pakhavaj", "tabla", "click")


@dataclass(frozen=True)
class StrokePattern:
    tala_id: str
    instrument: str
    strokes: tuple[str, ...]
    accents: tuple[int, ...]


def _load_patterns() -> dict[tuple[str, str], StrokePattern]:
    global _PATTERN_CACHE  # noqa: PLW0603
    if _PATTERN_CACHE is not None:
        return _PATTERN_CACHE

    with open(_PATTERN_PATH, encoding="utf-8") as f:
        data = json.load(f)
    out: dict[tuple[str, str], StrokePattern] = {}
    for entry in data["patterns"]:
        key = (entry["tala_id"], entry["instrument"])
        out[key] = StrokePattern(
            tala_id=entry["tala_id"],
            instrument=entry["instrument"],
            strokes=tuple(entry["strokes"]),
            accents=tuple(entry["accents"]),
        )
    _PATTERN_CACHE = out
    return out


def get_pattern(tala_id: str, instrument: str) -> StrokePattern:
    """Look up the stroke pattern for a tala × instrument combination.

    Falls back to the click pattern (one stroke per matra, sam accented) when
    no instrument-specific pattern is registered for this tala.
    """
    patterns = _load_patterns()
    key = (tala_id, instrument)
    if key in patterns:
        return patterns[key]

    # Fallback: synthesise a click-style pattern from the tala's vibhag marks
    db = load_tala_db()
    if tala_id not in db:
        raise KeyError(f"Unknown tala: {tala_id}")
    tala = db[tala_id]
    n = tala.total_aksharas
    strokes = ["normal"] * n
    accents = [1] * n
    accents[0] = 2  # sam
    return StrokePattern(
        tala_id=tala_id,
        instrument="click",
        strokes=tuple(strokes),
        accents=tuple(accents),
    )


def list_pattern_keys() -> list[tuple[str, str]]:
    return list(_load_patterns().keys())


# ---------------------------------------------------------------------------
# Audio rendering
# ---------------------------------------------------------------------------


def _accent_amplitude(accent: int) -> float:
    """Map accent code (0 khali / 1 normal / 2 sam) to playback amplitude."""
    if accent >= 2:
        return 1.0
    if accent == 1:
        return 0.7
    return 0.45  # khali


def render_tala_loop(
    tala_id: str,
    instrument: str = "mridangam",
    tempo_bpm: float = 80.0,
    num_cycles: int = 4,
    sr: int = _DEFAULT_SR,
) -> np.ndarray:
    """Render a tala loop to a float32 audio buffer.

    Args:
        tala_id: Tala identifier in the global tala DB.
        instrument: One of mridangam | pakhavaj | tabla | click.
        tempo_bpm: Tempo in beats per minute (each matra = 1 beat at 1x).
        num_cycles: How many full tala cycles to render (>=1).
        sr: Sample rate.

    Returns:
        Float32 numpy array of audio samples.

    Raises:
        ValueError: If instrument is unknown or tempo/num_cycles are invalid.
        KeyError: If tala_id is not in the database.
    """
    if instrument not in _AVAILABLE_INSTRUMENTS:
        raise ValueError(
            f"Unknown instrument: {instrument}. "
            f"Available: {_AVAILABLE_INSTRUMENTS}"
        )
    if tempo_bpm < 20 or tempo_bpm > 320:
        raise ValueError(f"tempo_bpm out of range: {tempo_bpm}")
    if num_cycles < 1 or num_cycles > 32:
        raise ValueError(f"num_cycles out of range: {num_cycles}")

    pattern = get_pattern(tala_id, instrument)
    if len(pattern.strokes) == 0:
        return np.zeros(0, dtype=np.float32)

    seconds_per_beat = 60.0 / tempo_bpm
    samples_per_beat = int(round(sr * seconds_per_beat))
    cycle_samples = samples_per_beat * len(pattern.strokes)
    total_samples = cycle_samples * num_cycles

    # Add a tail equal to one beat for the final stroke's decay
    total_samples += samples_per_beat

    audio = np.zeros(total_samples, dtype=np.float32)

    for cycle in range(num_cycles):
        cycle_start = cycle * cycle_samples
        for i, (stroke, accent) in enumerate(
            zip(pattern.strokes, pattern.accents)
        ):
            try:
                stroke_audio = synthesize_stroke(
                    pattern.instrument, stroke, sr=sr
                )
            except ValueError:
                # Unknown stroke for this instrument — skip silently rather
                # than fail the whole loop. (Pattern data has typos in v1.)
                continue
            amp = _accent_amplitude(accent)
            start = cycle_start + i * samples_per_beat
            end = min(start + len(stroke_audio), total_samples)
            audio[start:end] += stroke_audio[: end - start] * amp

    # Final normalise to keep peaks below clipping after summing strokes
    peak = float(np.max(np.abs(audio)))
    if peak > 0.95:
        audio = (audio / peak) * 0.95

    return audio


def get_pattern_dict(tala_id: str, instrument: str) -> dict:
    """JSON-friendly dict for the API."""
    p = get_pattern(tala_id, instrument)
    return {
        "tala_id": p.tala_id,
        "instrument": p.instrument,
        "strokes": list(p.strokes),
        "accents": list(p.accents),
    }
