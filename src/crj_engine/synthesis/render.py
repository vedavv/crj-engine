"""Composition-to-audio renderer — synthesize notation into WAV files.

Tone types:
  - sine: pure sine wave (clean, electronic)
  - voice: sine + harmonics with vibrato (vocal-like)
  - string: sawtooth-based with ADSR envelope (violin/veena-like)

All tones use ADSR envelopes for natural note shaping.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np

from crj_engine.tala.models import (
    Bar,
    Composition,
    Octave,
    SwaraNote,
)

_CONFIGS_DIR = Path(__file__).resolve().parents[3] / "configs"

# Cache for swara cent values
_SWARA_CENTS: dict[str, float] | None = None


def _load_swara_cents() -> dict[str, float]:
    """Load swara id -> cents mapping from swarasthanas.json."""
    global _SWARA_CENTS  # noqa: PLW0603
    if _SWARA_CENTS is not None:
        return _SWARA_CENTS

    path = _CONFIGS_DIR / "swarasthanas.json"
    with open(path) as f:
        data = json.load(f)

    cents = {}
    for s in data["swarasthanas"]:
        cents[s["id"]] = s["cents"]
        # Also add aliases
        for alias in s.get("aliases", []):
            if alias not in cents:
                cents[alias] = s["cents"]

    _SWARA_CENTS = cents
    return cents


class ToneType(Enum):
    """Available synthesis tone types."""

    SINE = "sine"       # pure sine wave
    VOICE = "voice"     # harmonics + vibrato (vocal-like)
    STRING = "string"   # sawtooth + ADSR (veena/violin-like)


@dataclass
class ADSREnvelope:
    """Attack-Decay-Sustain-Release envelope.

    Times are given as fractions of total note duration (0.0 to 1.0).
    """

    attack: float = 0.05    # fraction of note for attack ramp
    decay: float = 0.1      # fraction for decay to sustain level
    sustain: float = 0.8    # sustain amplitude (0-1)
    release: float = 0.15   # fraction for release ramp

    def apply(self, signal: np.ndarray) -> np.ndarray:
        """Apply the ADSR envelope to a signal."""
        n = len(signal)
        envelope = np.ones(n, dtype=np.float32)

        a_end = int(n * self.attack)
        d_end = a_end + int(n * self.decay)
        r_start = n - int(n * self.release)

        # Attack: ramp 0 -> 1
        if a_end > 0:
            envelope[:a_end] = np.linspace(0, 1, a_end)
        # Decay: ramp 1 -> sustain
        if d_end > a_end:
            envelope[a_end:d_end] = np.linspace(
                1, self.sustain, d_end - a_end,
            )
        # Sustain: hold at sustain level
        envelope[d_end:r_start] = self.sustain
        # Release: ramp sustain -> 0
        if r_start < n:
            envelope[r_start:] = np.linspace(
                self.sustain, 0, n - r_start,
            )

        return signal * envelope


# ---------------------------------------------------------------------------
# Tone generators
# ---------------------------------------------------------------------------

def _swara_to_freq(
    note: SwaraNote, reference_sa_hz: float,
) -> float | None:
    """Convert a SwaraNote to frequency in Hz.

    Returns None for rests ("-") and sustains (",").
    """
    if note.swara_id in ("-", ","):
        return None

    cents_map = _load_swara_cents()
    if note.swara_id not in cents_map:
        return None

    cents = cents_map[note.swara_id]

    # Apply octave offset
    if note.octave == Octave.MANDRA:
        cents -= 1200
    elif note.octave == Octave.TARA:
        cents += 1200

    return reference_sa_hz * (2 ** (cents / 1200.0))


def _generate_sine(
    freq_hz: float, duration_s: float, sr: int,
) -> np.ndarray:
    """Pure sine wave."""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    return np.sin(2 * np.pi * freq_hz * t).astype(np.float32)


def _generate_voice(
    freq_hz: float, duration_s: float, sr: int,
) -> np.ndarray:
    """Voice-like tone: fundamental + harmonics + gentle vibrato."""
    n = int(sr * duration_s)
    t = np.linspace(0, duration_s, n, endpoint=False)

    # Vibrato: 5 Hz, ±8 cents (subtle)
    vibrato_hz = 5.0
    vibrato_depth = freq_hz * (2 ** (8 / 1200.0) - 1)
    vibrato = vibrato_depth * np.sin(2 * np.pi * vibrato_hz * t)

    # Fundamental + harmonics (decreasing amplitude)
    signal = np.zeros(n, dtype=np.float64)
    harmonic_weights = [1.0, 0.5, 0.25, 0.15, 0.08]
    for i, weight in enumerate(harmonic_weights):
        h = i + 1
        signal += weight * np.sin(
            2 * np.pi * (freq_hz * h + vibrato * h) * t
        )

    # Normalize
    peak = np.max(np.abs(signal))
    if peak > 0:
        signal /= peak

    return signal.astype(np.float32)


def _generate_string(
    freq_hz: float, duration_s: float, sr: int,
) -> np.ndarray:
    """String-like tone: band-limited sawtooth approximation."""
    n = int(sr * duration_s)
    t = np.linspace(0, duration_s, n, endpoint=False)

    # Band-limited sawtooth (sum of harmonics)
    signal = np.zeros(n, dtype=np.float64)
    max_harmonic = min(20, int(sr / 2 / freq_hz))
    for h in range(1, max_harmonic + 1):
        signal += ((-1) ** (h + 1)) * np.sin(
            2 * np.pi * h * freq_hz * t
        ) / h

    signal *= 2 / np.pi  # normalize sawtooth amplitude

    # Normalize
    peak = np.max(np.abs(signal))
    if peak > 0:
        signal /= peak

    return signal.astype(np.float32)


_TONE_GENERATORS = {
    ToneType.SINE: _generate_sine,
    ToneType.VOICE: _generate_voice,
    ToneType.STRING: _generate_string,
}

# Tone-specific ADSR presets
_ADSR_PRESETS = {
    ToneType.SINE: ADSREnvelope(
        attack=0.02, decay=0.05, sustain=0.9, release=0.1,
    ),
    ToneType.VOICE: ADSREnvelope(
        attack=0.08, decay=0.1, sustain=0.7, release=0.15,
    ),
    ToneType.STRING: ADSREnvelope(
        attack=0.01, decay=0.15, sustain=0.6, release=0.2,
    ),
}


# ---------------------------------------------------------------------------
# Tanpura drone
# ---------------------------------------------------------------------------

def generate_tanpura(
    reference_sa_hz: float = 261.63,
    duration_s: float = 10.0,
    sr: int = 44100,
) -> np.ndarray:
    """Generate a tanpura-like drone (Sa-Pa-Sa-Sa pattern).

    The tanpura provides the tonal foundation with Sa and Pa
    as continuous drones with rich harmonics.

    Args:
        reference_sa_hz: The Sa frequency in Hz.
        duration_s: Duration of drone in seconds.
        sr: Sample rate.

    Returns:
        Audio samples as float32 numpy array.
    """
    n = int(sr * duration_s)
    t = np.linspace(0, duration_s, n, endpoint=False)

    pa_hz = reference_sa_hz * (2 ** (700 / 1200.0))  # Pa = 700 cents
    sa_upper = reference_sa_hz * 2  # upper octave Sa

    drone = np.zeros(n, dtype=np.float64)

    # 4 strings of tanpura: Pa, Sa(upper), Sa(upper), Sa(lower)
    strings = [
        (pa_hz, 0.3),
        (sa_upper, 0.35),
        (sa_upper, 0.35),
        (reference_sa_hz, 0.25),
    ]

    for freq, amp in strings:
        # Each string has rich harmonics (characteristic jivari buzz)
        for h in range(1, 8):
            weight = amp / (h ** 1.2)
            # Slight detuning for warmth
            detune = 1 + (h - 1) * 0.001
            drone += weight * np.sin(
                2 * np.pi * freq * h * detune * t
            )

    # Slow amplitude modulation (tanpura "breathing")
    breathing = 0.85 + 0.15 * np.sin(2 * np.pi * 0.15 * t)
    drone *= breathing

    # Normalize to -6 dB (leave headroom for melody)
    peak = np.max(np.abs(drone))
    if peak > 0:
        drone = drone / peak * 0.5

    return drone.astype(np.float32)


# ---------------------------------------------------------------------------
# Bar and Composition rendering
# ---------------------------------------------------------------------------

def render_bar_audio(
    bar: Bar,
    reference_sa_hz: float = 261.63,
    tempo_bpm: float = 60.0,
    tone: ToneType = ToneType.VOICE,
    sr: int = 44100,
    amplitude: float = 0.7,
) -> np.ndarray:
    """Render a single bar as audio.

    Args:
        bar: The Bar to render.
        reference_sa_hz: The Sa frequency in Hz.
        tempo_bpm: Tempo in beats per minute (1 akshara = 1 beat).
        tone: Which tone type to use.
        sr: Sample rate.
        amplitude: Overall amplitude (0-1).

    Returns:
        Audio samples as float32 numpy array.
    """
    beat_duration_s = 60.0 / tempo_bpm

    # Each position duration depends on speed
    position_duration_s = beat_duration_s / bar.speed.value

    generator = _TONE_GENERATORS[tone]
    adsr = _ADSR_PRESETS[tone]

    segments = []
    prev_freq: float | None = None

    for note in bar.swaras:
        n_samples = int(sr * position_duration_s)

        if note.swara_id == ",":
            # Sustain: continue previous note
            if prev_freq is not None:
                seg = generator(prev_freq, position_duration_s, sr)
                # No ADSR on sustain — just smooth continuation
                segments.append(seg * amplitude)
            else:
                segments.append(np.zeros(n_samples, dtype=np.float32))
        elif note.swara_id == "-":
            # Rest: silence
            segments.append(np.zeros(n_samples, dtype=np.float32))
            prev_freq = None
        else:
            freq = _swara_to_freq(note, reference_sa_hz)
            if freq is not None:
                seg = generator(freq, position_duration_s, sr)
                seg = adsr.apply(seg)
                segments.append(seg * amplitude)
                prev_freq = freq
            else:
                segments.append(np.zeros(n_samples, dtype=np.float32))
                prev_freq = None

    if not segments:
        return np.zeros(0, dtype=np.float32)

    return np.concatenate(segments)


def render_composition(
    comp: Composition,
    tempo_bpm: float = 60.0,
    tone: ToneType = ToneType.VOICE,
    sr: int = 44100,
    include_tanpura: bool = True,
    amplitude: float = 0.7,
) -> np.ndarray:
    """Render a full composition as audio.

    Args:
        comp: The Composition to render.
        tempo_bpm: Tempo in BPM.
        tone: Tone type for melody.
        sr: Sample rate.
        include_tanpura: Whether to add tanpura drone background.
        amplitude: Melody amplitude.

    Returns:
        Audio samples as float32 numpy array.
    """
    melody_parts = []

    for section in comp.sections:
        for line in section.lines:
            # Render each repeat
            line_audio_parts = []
            for bar in line.bars:
                bar_audio = render_bar_audio(
                    bar, comp.reference_sa_hz, tempo_bpm, tone, sr,
                    amplitude,
                )
                line_audio_parts.append(bar_audio)

            line_audio = np.concatenate(line_audio_parts)

            # Repeat the line
            for _ in range(line.repeat):
                melody_parts.append(line_audio)

    if not melody_parts:
        return np.zeros(0, dtype=np.float32)

    melody = np.concatenate(melody_parts)

    if include_tanpura:
        duration_s = len(melody) / sr
        tanpura = generate_tanpura(
            comp.reference_sa_hz, duration_s, sr,
        )
        # Mix: melody + tanpura
        min_len = min(len(melody), len(tanpura))
        mixed = np.zeros(max(len(melody), len(tanpura)),
                         dtype=np.float32)
        mixed[:len(melody)] += melody
        mixed[:len(tanpura)] += tanpura[:min_len]

        # Soft-clip to prevent clipping
        peak = np.max(np.abs(mixed))
        if peak > 0.95:
            mixed = mixed / peak * 0.95

        return mixed

    return melody


def save_wav(
    audio: np.ndarray,
    path: str | Path,
    sr: int = 44100,
) -> None:
    """Save audio to a WAV file.

    Args:
        audio: Audio samples as float32 numpy array.
        path: Output file path.
        sr: Sample rate.
    """
    import soundfile as sf

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), audio, sr, subtype="FLOAT")
