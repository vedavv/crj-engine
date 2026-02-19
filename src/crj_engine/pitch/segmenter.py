"""Pitch contour segmentation — split a PitchContour into windows for gamaka classification."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from crj_engine.pitch.detector import PitchContour


@dataclass
class PitchSegment:
    """A windowed segment of a pitch contour, ready for gamaka analysis.

    Attributes:
        start_ms: Start time of the segment in milliseconds.
        end_ms: End time of the segment in milliseconds.
        frequencies: Array of F0 values (Hz) within this segment.
        reference_sa_hz: The tonic Sa frequency used for cents conversion.
        cents_from_sa: Array of cent values relative to Sa for each frame.
    """

    start_ms: float
    end_ms: float
    frequencies: np.ndarray
    reference_sa_hz: float
    cents_from_sa: np.ndarray

    @property
    def duration_ms(self) -> float:
        """Duration of this segment in milliseconds."""
        return self.end_ms - self.start_ms

    @property
    def num_frames(self) -> int:
        """Number of frames in this segment."""
        return len(self.frequencies)


def _freq_to_cents(freq: float, reference_sa_hz: float) -> float:
    """Convert a single frequency to cents relative to Sa.

    Returns NaN for non-positive frequencies (unvoiced frames).
    """
    if freq <= 0 or reference_sa_hz <= 0:
        return float("nan")
    return 1200.0 * math.log2(freq / reference_sa_hz)


def segment_contour(
    contour: PitchContour,
    window_ms: float = 300.0,
    hop_ms: float = 100.0,
    min_voiced_ratio: float = 0.7,
    confidence_threshold: float = 0.5,
    reference_sa_hz: float = 261.63,
) -> list[PitchSegment]:
    """Segment a pitch contour into overlapping windows for gamaka classification.

    The contour is split into overlapping windows of ``window_ms`` duration,
    advancing by ``hop_ms`` each step.  Only windows where at least
    ``min_voiced_ratio`` of frames are voiced (confidence >= threshold) are
    kept.

    Args:
        contour: The full PitchContour from pitch detection.
        window_ms: Window size in milliseconds (200-500 ms typical).
        hop_ms: Hop between successive windows in milliseconds.
        min_voiced_ratio: Minimum fraction of frames that must be voiced
            (confidence >= confidence_threshold) for the segment to be included.
        confidence_threshold: Frames with confidence below this are considered
            unvoiced.
        reference_sa_hz: The tonic Sa frequency in Hz for cents calculation.

    Returns:
        List of PitchSegment instances, one per valid window.
    """
    if not contour.frames:
        return []

    timestamps = contour.timestamps
    frequencies = contour.frequencies
    confidences = contour.confidences

    total_duration = timestamps[-1]
    segments: list[PitchSegment] = []

    start = timestamps[0]
    while start + window_ms <= total_duration + contour.hop_ms:
        end = start + window_ms

        # Select frames within [start, end)
        mask = (timestamps >= start) & (timestamps < end)
        window_freqs = frequencies[mask]
        window_confs = confidences[mask]

        if len(window_freqs) == 0:
            start += hop_ms
            continue

        # Check voiced ratio
        voiced_count = np.sum(window_confs >= confidence_threshold)
        voiced_ratio = voiced_count / len(window_confs)

        if voiced_ratio < min_voiced_ratio:
            start += hop_ms
            continue

        # Convert voiced frequencies to cents from Sa; unvoiced frames get NaN
        cents = np.array([
            _freq_to_cents(f, reference_sa_hz)
            if conf >= confidence_threshold
            else float("nan")
            for f, conf in zip(window_freqs, window_confs, strict=True)
        ])

        segments.append(PitchSegment(
            start_ms=start,
            end_ms=end,
            frequencies=window_freqs.copy(),
            reference_sa_hz=reference_sa_hz,
            cents_from_sa=cents,
        ))

        start += hop_ms

    return segments
