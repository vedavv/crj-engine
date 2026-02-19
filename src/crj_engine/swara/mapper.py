"""Swara mapping — convert frequencies to Western notes and Indian swarasthanas."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

_CONFIGS_DIR = Path(__file__).resolve().parents[3] / "configs"

# Western note names in chromatic order
_WESTERN_NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


@dataclass
class WesternNote:
    """A Western musical note."""

    name: str
    octave: int
    frequency_hz: float
    cents_deviation: float  # deviation from exact tempered pitch


@dataclass
class SwaraMatch:
    """A matched Indian classical swara."""

    swara_id: str
    cents_from_sa: float
    cents_deviation: float  # deviation from exact swara position
    frequency_hz: float
    names: dict[str, str]  # script -> name
    full_names: dict[str, str]  # script -> full name
    aliases: list[str]  # enharmonic alternatives
    confidence: float  # how close the match is (1.0 = exact)


def freq_to_western(freq_hz: float, a4_hz: float = 440.0) -> WesternNote:
    """Convert a frequency to the nearest Western note.

    Args:
        freq_hz: Frequency in Hz.
        a4_hz: Reference frequency for A4 (default 440 Hz).

    Returns:
        WesternNote with name, octave, and cents deviation.
    """
    if freq_hz <= 0:
        return WesternNote(name="—", octave=0, frequency_hz=0, cents_deviation=0)

    # Semitones from A4
    semitones_from_a4 = 12 * math.log2(freq_hz / a4_hz)
    midi_number = round(semitones_from_a4) + 69

    note_index = midi_number % 12
    octave = (midi_number // 12) - 1

    # Exact frequency of the nearest note
    exact_freq = a4_hz * (2 ** ((midi_number - 69) / 12))
    cents_deviation = 1200 * math.log2(freq_hz / exact_freq)

    return WesternNote(
        name=_WESTERN_NOTES[note_index],
        octave=octave,
        frequency_hz=freq_hz,
        cents_deviation=cents_deviation,
    )


def freq_to_swara(
    freq_hz: float,
    reference_sa_hz: float = 261.63,
    tolerance_cents: float = 25.0,
    swarasthanas: list[dict] | None = None,
) -> SwaraMatch | None:
    """Convert a frequency to the nearest Indian classical swara.

    Args:
        freq_hz: Frequency in Hz.
        reference_sa_hz: Frequency of the tonic Sa in Hz.
        tolerance_cents: Maximum allowed deviation in cents for a match.
        swarasthanas: Swara definitions (loaded from config if None).

    Returns:
        SwaraMatch if a swara is within tolerance, else None.
    """
    if freq_hz <= 0:
        return None

    if swarasthanas is None:
        swarasthanas = _load_swarasthanas()

    # Calculate cents from Sa (modulo octave = 1200 cents)
    cents_from_sa = 1200 * math.log2(freq_hz / reference_sa_hz)
    # Normalize to within one octave (0–1200)
    cents_in_octave = cents_from_sa % 1200

    # Find the closest swara
    best_match = None
    best_deviation = float("inf")

    for swara in swarasthanas:
        swara_cents = swara["cents"]
        deviation = cents_in_octave - swara_cents

        # Handle wrap-around (e.g., 1190 cents is close to Sa at 0)
        if deviation > 600:
            deviation -= 1200
        elif deviation < -600:
            deviation += 1200

        abs_deviation = abs(deviation)
        if abs_deviation < best_deviation:
            best_deviation = abs_deviation
            best_match = swara
            best_cents_deviation = deviation

    if best_match is None or best_deviation > tolerance_cents:
        return None

    # Confidence: 1.0 at exact match, 0.0 at tolerance boundary
    confidence = max(0.0, 1.0 - (best_deviation / tolerance_cents))

    return SwaraMatch(
        swara_id=best_match["id"],
        cents_from_sa=cents_in_octave,
        cents_deviation=best_cents_deviation,
        frequency_hz=freq_hz,
        names=best_match["names"],
        full_names=best_match["full_names"],
        aliases=best_match.get("aliases", []),
        confidence=confidence,
    )


def _load_swarasthanas() -> list[dict]:
    """Load swarasthana definitions from the config file."""
    config_path = _CONFIGS_DIR / "swarasthanas.json"
    with open(config_path) as f:
        data = json.load(f)
    return data["swarasthanas"]
