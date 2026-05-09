"""Synthesised percussion strokes — Mridangam, Pakhavaj, Tabla.

Each stroke is a one-shot ~100-200 ms audio buffer built from:
  - A pitched body (sum of decaying sinusoids tuned to the drum's resonance)
  - A noise transient (filtered short burst for the strike)
  - An exponential decay envelope

This is the v1 "synth voices" implementation. A future "premium voices"
package will swap these for sampled real recordings of the same instruments;
the public API (synthesize_stroke + StrokeSpec) stays the same so the
tala_engine doesn't need to change.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

_DEFAULT_SR = 44100


@dataclass(frozen=True)
class StrokeSpec:
    """Parametric description of a single percussion stroke."""

    body_freqs_hz: tuple[float, ...]
    body_weights: tuple[float, ...]
    body_decay_s: float
    noise_amp: float
    noise_decay_s: float
    noise_lowpass_hz: float
    duration_s: float
    inharmonicity: float = 0.0


# ---------------------------------------------------------------------------
# Stroke palettes
# ---------------------------------------------------------------------------
# Mridangam (Carnatic) — wood shell, two heads (right=high, left=low/bass).

_MRIDANGAM = {
    "ta":  StrokeSpec((520, 1040, 1560), (1.0, 0.55, 0.25), 0.10, 0.55, 0.018, 6500, 0.18),
    "ki":  StrokeSpec((780, 1500), (1.0, 0.40), 0.06, 0.45, 0.012, 7500, 0.10),
    "thom": StrokeSpec((90, 130, 250), (1.0, 0.7, 0.4), 0.45, 0.30, 0.025, 1800, 0.40, inharmonicity=0.005),
    "nam": StrokeSpec((420, 720), (1.0, 0.5), 0.20, 0.40, 0.020, 3500, 0.22),
    "din": StrokeSpec((300, 600, 900), (1.0, 0.55, 0.3), 0.30, 0.35, 0.020, 4500, 0.30),
    "dhi": StrokeSpec((140, 250, 600), (0.9, 0.5, 0.7), 0.30, 0.45, 0.020, 4000, 0.30),
    "tom": StrokeSpec((110, 200, 320), (1.0, 0.6, 0.3), 0.40, 0.30, 0.022, 2200, 0.35),
    "ka":  StrokeSpec((250, 500), (0.9, 0.4), 0.10, 0.55, 0.014, 5500, 0.14),
    "jham": StrokeSpec((180, 360, 720), (0.9, 0.7, 0.4), 0.40, 0.55, 0.025, 5000, 0.40, inharmonicity=0.01),
}

# Pakhavaj (Dhrupad) — larger barrel drum, deeper resonance, longer sustain.

_PAKHAVAJ = {
    "dha": StrokeSpec((85, 170, 260), (1.0, 0.7, 0.45), 0.55, 0.40, 0.025, 2200, 0.55),
    "ga":  StrokeSpec((75, 140), (1.0, 0.5), 0.55, 0.30, 0.025, 1600, 0.55),
    "di":  StrokeSpec((220, 440, 660), (1.0, 0.5, 0.3), 0.30, 0.35, 0.020, 4000, 0.32),
    "na":  StrokeSpec((360, 700), (1.0, 0.45), 0.20, 0.40, 0.020, 3500, 0.22),
    "tat": StrokeSpec((480, 960), (1.0, 0.4), 0.12, 0.55, 0.014, 6000, 0.18),
    "dhin": StrokeSpec((200, 400, 600), (1.0, 0.5, 0.3), 0.45, 0.40, 0.025, 3500, 0.45),
    "kat": StrokeSpec((180, 320), (1.0, 0.4), 0.15, 0.50, 0.018, 3000, 0.20),
    "terekita": StrokeSpec((400, 700), (0.9, 0.4), 0.08, 0.65, 0.025, 5000, 0.26),
}

# Tabla (Hindustani) — bayan (low) + tabla (high), bright transients.

_TABLA = {
    "dha":  StrokeSpec((90, 280, 560), (1.0, 0.7, 0.4), 0.40, 0.45, 0.020, 4500, 0.40),
    "dhin": StrokeSpec((280, 560, 840), (1.0, 0.55, 0.3), 0.35, 0.35, 0.018, 5000, 0.36),
    "ti":   StrokeSpec((600, 1200), (1.0, 0.4), 0.06, 0.55, 0.012, 7500, 0.10),
    "ta":   StrokeSpec((680, 1360), (1.0, 0.4), 0.06, 0.55, 0.012, 7500, 0.10),
    "na":   StrokeSpec((420, 840), (1.0, 0.45), 0.20, 0.40, 0.018, 4000, 0.22),
    "tin":  StrokeSpec((520, 1040), (1.0, 0.45), 0.12, 0.50, 0.014, 6500, 0.16),
    "ge":   StrokeSpec((85, 130, 200), (1.0, 0.6, 0.3), 0.50, 0.30, 0.025, 1700, 0.50, inharmonicity=0.005),
    "ke":   StrokeSpec((75, 150), (1.0, 0.5), 0.10, 0.55, 0.022, 1800, 0.16),
    "terekita": StrokeSpec((500, 1000), (0.9, 0.4), 0.06, 0.65, 0.012, 6500, 0.10),
    "dhage": StrokeSpec((120, 240, 480), (1.0, 0.6, 0.4), 0.30, 0.45, 0.020, 4000, 0.30),
}

# Generic click-track strokes (woodblock / verbal-tick alternative).

_CLICK = {
    "accent":  StrokeSpec((1500, 3000), (1.0, 0.5), 0.04, 0.6, 0.008, 8000, 0.06),
    "normal":  StrokeSpec((1100,), (1.0,), 0.03, 0.45, 0.006, 7000, 0.05),
    "mute":    StrokeSpec((900,), (1.0,), 0.025, 0.30, 0.005, 5000, 0.04),
}


_INSTRUMENT_PALETTES = {
    "mridangam": _MRIDANGAM,
    "pakhavaj": _PAKHAVAJ,
    "tabla": _TABLA,
    "click": _CLICK,
}


def list_strokes(instrument: str) -> list[str]:
    """Return the available stroke names for an instrument."""
    return list(_INSTRUMENT_PALETTES[instrument].keys())


def list_instruments() -> list[str]:
    return list(_INSTRUMENT_PALETTES.keys())


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------


def _filtered_noise(n: int, sr: int, lowpass_hz: float) -> np.ndarray:
    """Cheap one-pole lowpass-filtered white noise."""
    noise = np.random.uniform(-1.0, 1.0, n).astype(np.float64)
    if lowpass_hz <= 0 or lowpass_hz >= sr / 2:
        return noise
    # First-order RC lowpass coefficient
    rc = 1.0 / (2 * np.pi * lowpass_hz)
    dt = 1.0 / sr
    alpha = dt / (rc + dt)
    out = np.zeros(n, dtype=np.float64)
    prev = 0.0
    for i in range(n):
        prev = prev + alpha * (noise[i] - prev)
        out[i] = prev
    # Boost back since lowpass attenuates
    peak = np.max(np.abs(out))
    if peak > 0:
        out = out / peak
    return out


def _synthesize(spec: StrokeSpec, sr: int) -> np.ndarray:
    n = int(sr * spec.duration_s)
    if n <= 0:
        return np.zeros(0, dtype=np.float32)
    t = np.linspace(0, spec.duration_s, n, endpoint=False)

    # Tonal body — harmonics with exponential decay
    body = np.zeros(n, dtype=np.float64)
    for i, (freq, weight) in enumerate(zip(spec.body_freqs_hz, spec.body_weights)):
        # Slight harmonic detune for inharmonicity (drum heads aren't perfect)
        f = freq * (1.0 + spec.inharmonicity * i)
        body += weight * np.sin(2 * np.pi * f * t)
    body_env = np.exp(-t / max(spec.body_decay_s, 1e-3))
    body *= body_env

    # Strike transient — filtered noise burst
    if spec.noise_amp > 0:
        noise = _filtered_noise(n, sr, spec.noise_lowpass_hz)
        noise_env = np.exp(-t / max(spec.noise_decay_s, 1e-4))
        body += spec.noise_amp * noise * noise_env

    # Normalize to -3 dB peak for headroom when mixed with other strokes
    peak = float(np.max(np.abs(body)))
    if peak > 0:
        body = body / peak * 0.7

    return body.astype(np.float32)


@lru_cache(maxsize=128)
def _synthesize_cached(
    instrument: str, stroke: str, sr: int
) -> np.ndarray:
    palette = _INSTRUMENT_PALETTES.get(instrument)
    if palette is None:
        raise ValueError(f"Unknown instrument: {instrument}")
    spec = palette.get(stroke)
    if spec is None:
        raise ValueError(
            f"Unknown stroke '{stroke}' for {instrument}. "
            f"Available: {list(palette.keys())}"
        )
    # NB: lru_cache returns the array by reference — callers must not mutate.
    return _synthesize(spec, sr)


def synthesize_stroke(
    instrument: str, stroke: str, sr: int = _DEFAULT_SR
) -> np.ndarray:
    """Return a one-shot stroke as a copy (safe to mutate)."""
    return _synthesize_cached(instrument, stroke, sr).copy()
