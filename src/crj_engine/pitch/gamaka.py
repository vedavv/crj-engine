"""Gamaka classification — rule-based identification of ornament types from pitch segments.

MVP gamaka types:
  - Kampita: oscillation / vibrato around a note
  - Jaru: smooth glide between two notes
  - Sphuritham: quick touch of adjacent note then return

A future phase will replace / augment this with a CNN-LSTM classifier trained on
annotated Carnatic vocal data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from crj_engine.pitch.segmenter import PitchSegment


class GamakaType(Enum):
    """Recognised gamaka ornament types (MVP set + steady baseline)."""

    KAMPITA = "kampita"
    JARU = "jaru"
    SPHURITHAM = "sphuritham"
    STEADY = "steady"


@dataclass
class GamakaResult:
    """Classification result for a single pitch segment.

    Attributes:
        gamaka_type: The identified gamaka type (or "steady").
        confidence: Classification confidence in [0, 1].
        details: Extra diagnostic information (varies by type).
    """

    gamaka_type: str
    confidence: float
    details: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Internal feature extraction
# ---------------------------------------------------------------------------

def _clean_cents(cents: np.ndarray) -> np.ndarray:
    """Return a copy with NaN values interpolated (linear) so downstream
    calculations are not disrupted by occasional unvoiced frames."""
    clean = cents.copy()
    nans = np.isnan(clean)
    if nans.all():
        return clean  # nothing to interpolate
    if nans.any():
        indices = np.arange(len(clean))
        clean[nans] = np.interp(indices[nans], indices[~nans], clean[~nans])
    return clean


def _first_derivative(cents: np.ndarray) -> np.ndarray:
    """Frame-to-frame first derivative of the cent contour."""
    if len(cents) < 2:
        return np.zeros_like(cents)
    return np.diff(cents, prepend=cents[0])


def _zero_crossings(signal: np.ndarray) -> int:
    """Count zero-crossings (sign changes) in *signal*."""
    if len(signal) < 2:
        return 0
    signs = np.sign(signal)
    # Ignore exact zeros — treat them as continuation of previous sign
    signs[signs == 0] = 1
    return int(np.sum(np.diff(signs) != 0))


# ---------------------------------------------------------------------------
# Individual classifiers
# ---------------------------------------------------------------------------

def _detect_kampita(
    cents: np.ndarray,
    deriv: np.ndarray,
    zc: int,
    pitch_range: float,
    duration_ms: float,
) -> GamakaResult | None:
    """Kampita: periodic oscillation / vibrato around a note.

    Heuristic:
    - At least 3 zero-crossings in the derivative (i.e. >= 2 oscillation cycles)
    - Pitch range between 20 and 250 cents (too narrow = steady, too wide = jaru)
    - Duration >= 150 ms
    """
    if duration_ms < 150:
        return None

    # Require meaningful oscillation amplitude
    if pitch_range < 20 or pitch_range > 250:
        return None

    # Require enough oscillation cycles.  2 full cycles -> 4 zero-crossings in
    # the derivative, but be generous and accept >= 3.
    min_crossings = 3
    if zc < min_crossings:
        return None

    # Confidence: higher when oscillation is more periodic (more crossings,
    # moderate range).
    osc_score = min(1.0, zc / 10.0)
    range_score = 1.0 - abs(pitch_range - 80) / 200.0  # peak confidence ~80 cents
    range_score = max(0.0, min(1.0, range_score))
    confidence = 0.6 * osc_score + 0.4 * range_score

    return GamakaResult(
        gamaka_type=GamakaType.KAMPITA.value,
        confidence=round(float(confidence), 3),
        details={
            "zero_crossings": zc,
            "pitch_range_cents": round(float(pitch_range), 2),
            "duration_ms": round(duration_ms, 2),
        },
    )


def _detect_jaru(
    cents: np.ndarray,
    deriv: np.ndarray,
    zc: int,
    pitch_range: float,
    duration_ms: float,
) -> GamakaResult | None:
    """Jaru: smooth monotonic glide between two notes.

    Heuristic:
    - Net pitch change (last - first) > 50 cents in absolute value
    - Few zero-crossings in the derivative (mostly one direction)
    - Pitch range dominated by net change (not oscillatory)
    """
    if len(cents) < 3:
        return None

    net_change = cents[-1] - cents[0]
    abs_net = abs(net_change)

    if abs_net < 50:
        return None

    # Monotonicity: ratio of net change to pitch range.
    # A perfect glide has ratio ~1.0; oscillatory motion has ratio << 1.
    monotonicity = abs_net / max(pitch_range, 1e-6)
    if monotonicity < 0.5:
        return None

    # Low zero-crossings reinforces monotonic motion
    if zc > 6:
        return None

    direction = "ascending" if net_change > 0 else "descending"
    confidence = min(1.0, monotonicity) * min(1.0, abs_net / 100.0)
    confidence = max(0.0, min(1.0, confidence))

    return GamakaResult(
        gamaka_type=GamakaType.JARU.value,
        confidence=round(float(confidence), 3),
        details={
            "net_change_cents": round(float(net_change), 2),
            "direction": direction,
            "monotonicity": round(float(monotonicity), 3),
            "pitch_range_cents": round(float(pitch_range), 2),
        },
    )


def _detect_sphuritham(
    cents: np.ndarray,
    deriv: np.ndarray,
    hop_ms: float,
    pitch_range: float,
    duration_ms: float,
    zc: int = 0,
) -> GamakaResult | None:
    """Sphuritham: quick touch of an adjacent note and return.

    Heuristic:
    - There exists a brief spike (> 50 cents from the base pitch) lasting < 100 ms
    - The contour returns to approximately the base pitch (within 25 cents)
    - Base pitch is estimated as the median of the segment
    - NOT oscillatory: derivative zero-crossings must be low (< 3)
    """
    if len(cents) < 4:
        return None

    # If the derivative has many zero-crossings, this is oscillatory (Kampita),
    # not a touch-and-return (Sphuritham).
    if zc >= 3:
        return None

    base_pitch = float(np.median(cents))
    deviation = cents - base_pitch

    # Identify spike frames: > 50 cents from base
    spike_mask = np.abs(deviation) > 50
    if not np.any(spike_mask):
        return None

    # Find contiguous spike runs and check their duration
    spike_indices = np.where(spike_mask)[0]
    runs: list[tuple[int, int]] = []
    run_start = spike_indices[0]
    for i in range(1, len(spike_indices)):
        if spike_indices[i] != spike_indices[i - 1] + 1:
            runs.append((run_start, spike_indices[i - 1]))
            run_start = spike_indices[i]
    runs.append((run_start, spike_indices[-1]))

    # Check each run: must be short (<100ms) and segment must return to base
    best_spike: dict | None = None
    for rs, re in runs:
        run_duration = (re - rs + 1) * hop_ms
        if run_duration >= 100:
            continue  # spike too long

        peak_deviation = float(np.max(np.abs(deviation[rs : re + 1])))

        # Check that the segment returns to base after the spike
        # (within 25 cents of base in the tail after the spike)
        tail_start = re + 1
        if tail_start < len(cents):
            tail_mean_dev = float(np.mean(np.abs(deviation[tail_start:])))
        else:
            # Spike at the very end; check the head instead
            tail_mean_dev = float(np.mean(np.abs(deviation[: rs]))) if rs > 0 else 999.0

        if tail_mean_dev > 25:
            continue

        if best_spike is None or peak_deviation > best_spike["peak_deviation"]:
            best_spike = {
                "peak_deviation": peak_deviation,
                "spike_duration_ms": run_duration,
                "tail_mean_deviation": tail_mean_dev,
            }

    if best_spike is None:
        return None

    # Confidence based on how clearly the spike stands out
    spike_clarity = min(1.0, best_spike["peak_deviation"] / 100.0)
    return_quality = max(0.0, 1.0 - best_spike["tail_mean_deviation"] / 25.0)
    confidence = 0.5 * spike_clarity + 0.5 * return_quality

    return GamakaResult(
        gamaka_type=GamakaType.SPHURITHAM.value,
        confidence=round(float(confidence), 3),
        details={
            "peak_deviation_cents": round(best_spike["peak_deviation"], 2),
            "spike_duration_ms": round(best_spike["spike_duration_ms"], 2),
            "base_pitch_cents": round(base_pitch, 2),
        },
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify_gamaka(
    segment: PitchSegment,
    hop_ms: float = 10.0,
) -> GamakaResult:
    """Classify the gamaka type present in a pitch segment.

    The classifiers are evaluated in priority order: Sphuritham (most specific
    pattern), then Kampita, then Jaru, and finally Steady as the default.

    Args:
        segment: A PitchSegment produced by the segmenter.
        hop_ms: The hop size in milliseconds between successive frames.
            Used to estimate spike durations for Sphuritham detection.

    Returns:
        A GamakaResult describing the detected ornament.
    """
    cents = _clean_cents(segment.cents_from_sa)

    # If the segment is entirely NaN (all unvoiced), return steady with 0 confidence
    if np.isnan(cents).all():
        return GamakaResult(
            gamaka_type=GamakaType.STEADY.value,
            confidence=0.0,
            details={"reason": "all_unvoiced"},
        )

    deriv = _first_derivative(cents)
    zc = _zero_crossings(deriv)
    pitch_range = float(np.nanmax(cents) - np.nanmin(cents))
    duration_ms = segment.duration_ms

    # Priority order: Sphuritham > Kampita > Jaru > Steady
    # Sphuritham is the most specific (short spike + return); test first.
    result = _detect_sphuritham(cents, deriv, hop_ms, pitch_range, duration_ms, zc)
    if result is not None:
        return result

    result = _detect_kampita(cents, deriv, zc, pitch_range, duration_ms)
    if result is not None:
        return result

    result = _detect_jaru(cents, deriv, zc, pitch_range, duration_ms)
    if result is not None:
        return result

    # Default: steady note (no ornament detected)
    return GamakaResult(
        gamaka_type=GamakaType.STEADY.value,
        confidence=round(float(max(0.0, 1.0 - pitch_range / 20.0)), 3),
        details={
            "pitch_range_cents": round(pitch_range, 2),
            "zero_crossings": zc,
        },
    )
