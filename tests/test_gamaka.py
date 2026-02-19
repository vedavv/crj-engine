"""Tests for gamaka classification — segmenter and rule-based classifier.

All tests use synthetic pitch contours built from numpy arrays, so no audio
files or heavy ML dependencies are required.
"""

import numpy as np
import pytest

from crj_engine.pitch.detector import PitchAlgorithm, PitchContour, PitchFrame
from crj_engine.pitch.gamaka import GamakaType, classify_gamaka
from crj_engine.pitch.segmenter import PitchSegment, segment_contour

# ---------------------------------------------------------------------------
# Helpers — build synthetic PitchContour objects
# ---------------------------------------------------------------------------

REFERENCE_SA_HZ = 261.63
HOP_MS = 10.0


def _make_contour(
    frequencies: np.ndarray,
    hop_ms: float = HOP_MS,
    confidence: float = 0.95,
) -> PitchContour:
    """Build a PitchContour from a frequency array.

    Every frame gets the same confidence by default.
    """
    frames = [
        PitchFrame(
            timestamp_ms=i * hop_ms,
            frequency_hz=float(f),
            confidence=confidence,
        )
        for i, f in enumerate(frequencies)
    ]
    return PitchContour(
        frames=frames,
        algorithm=PitchAlgorithm.PYIN,
        sample_rate=16000,
        hop_ms=hop_ms,
    )


def _cents_to_freq(cents: float, sa_hz: float = REFERENCE_SA_HZ) -> float:
    """Convert cents-from-Sa back to Hz."""
    return sa_hz * (2 ** (cents / 1200.0))


def _make_segment(
    cents_array: np.ndarray,
    hop_ms: float = HOP_MS,
    sa_hz: float = REFERENCE_SA_HZ,
) -> PitchSegment:
    """Build a PitchSegment directly from a cents array (convenience for
    classifier-only tests)."""
    freqs = np.array([_cents_to_freq(c, sa_hz) for c in cents_array])
    duration_ms = (len(cents_array) - 1) * hop_ms
    return PitchSegment(
        start_ms=0.0,
        end_ms=duration_ms,
        frequencies=freqs,
        reference_sa_hz=sa_hz,
        cents_from_sa=cents_array.copy(),
    )


# ---------------------------------------------------------------------------
# Segmenter tests
# ---------------------------------------------------------------------------

class TestSegmenter:
    """Tests for segment_contour()."""

    def test_empty_contour_returns_no_segments(self):
        contour = PitchContour(
            frames=[], algorithm=PitchAlgorithm.PYIN, sample_rate=16000, hop_ms=HOP_MS
        )
        segments = segment_contour(contour)
        assert segments == []

    def test_steady_tone_produces_segments(self):
        """A 1-second steady tone should produce multiple overlapping segments."""
        n_frames = 100  # 100 * 10 ms = 1000 ms
        freqs = np.full(n_frames, REFERENCE_SA_HZ)
        contour = _make_contour(freqs)
        segments = segment_contour(
            contour,
            window_ms=300.0,
            hop_ms=100.0,
            reference_sa_hz=REFERENCE_SA_HZ,
        )
        assert len(segments) > 0
        for seg in segments:
            assert seg.duration_ms == pytest.approx(300.0, abs=1.0)
            assert seg.num_frames > 0
            assert seg.reference_sa_hz == REFERENCE_SA_HZ

    def test_segment_cents_values(self):
        """Cents values should be close to 0 for a steady Sa tone."""
        n_frames = 50
        freqs = np.full(n_frames, REFERENCE_SA_HZ)
        contour = _make_contour(freqs)
        segments = segment_contour(
            contour,
            window_ms=300.0,
            hop_ms=100.0,
            reference_sa_hz=REFERENCE_SA_HZ,
        )
        assert len(segments) > 0
        for seg in segments:
            # All cents should be ~0 for Sa
            valid = seg.cents_from_sa[~np.isnan(seg.cents_from_sa)]
            assert np.all(np.abs(valid) < 1.0)

    def test_low_confidence_frames_excluded(self):
        """Segments where most frames are unvoiced should be dropped."""
        n_frames = 50
        freqs = np.full(n_frames, 300.0)
        # Build contour with low confidence
        contour = _make_contour(freqs, confidence=0.1)
        segments = segment_contour(
            contour,
            window_ms=300.0,
            hop_ms=100.0,
            confidence_threshold=0.5,
            min_voiced_ratio=0.7,
        )
        assert len(segments) == 0

    def test_segment_window_boundaries(self):
        """Each segment's start_ms < end_ms and they advance by hop."""
        n_frames = 80
        freqs = np.full(n_frames, REFERENCE_SA_HZ)
        contour = _make_contour(freqs)
        segments = segment_contour(
            contour, window_ms=200.0, hop_ms=50.0, reference_sa_hz=REFERENCE_SA_HZ
        )
        assert len(segments) >= 2
        for seg in segments:
            assert seg.start_ms < seg.end_ms
        # Segments should advance by hop
        for i in range(1, len(segments)):
            assert segments[i].start_ms == pytest.approx(
                segments[i - 1].start_ms + 50.0, abs=1.0
            )

    def test_mixed_confidence_contour(self):
        """Segments with enough voiced frames should still be included even if
        some frames have low confidence."""
        n_frames = 40  # 400 ms
        frames = []
        for i in range(n_frames):
            # Every 5th frame is unvoiced (20% unvoiced -> 80% voiced)
            conf = 0.1 if i % 5 == 0 else 0.9
            frames.append(
                PitchFrame(
                    timestamp_ms=i * HOP_MS,
                    frequency_hz=REFERENCE_SA_HZ,
                    confidence=conf,
                )
            )
        contour = PitchContour(
            frames=frames,
            algorithm=PitchAlgorithm.PYIN,
            sample_rate=16000,
            hop_ms=HOP_MS,
        )
        segments = segment_contour(
            contour,
            window_ms=300.0,
            hop_ms=100.0,
            min_voiced_ratio=0.7,
            confidence_threshold=0.5,
            reference_sa_hz=REFERENCE_SA_HZ,
        )
        # 80% voiced > 70% threshold, so segments should be produced
        assert len(segments) > 0


# ---------------------------------------------------------------------------
# Gamaka classifier tests
# ---------------------------------------------------------------------------

class TestKampitaDetection:
    """Kampita = oscillation / vibrato around a note."""

    def test_vibrato_detected_as_kampita(self):
        """Synthetic vibrato: sinusoidal oscillation around Pa (700 cents)."""
        n_frames = 40  # 400 ms at 10 ms hop
        t = np.arange(n_frames) * HOP_MS / 1000.0  # seconds
        # 5 Hz vibrato, +/- 40 cents around Pa
        cents = 700.0 + 40.0 * np.sin(2 * np.pi * 5.0 * t)
        segment = _make_segment(cents)
        result = classify_gamaka(segment, hop_ms=HOP_MS)
        assert result.gamaka_type == GamakaType.KAMPITA.value
        assert result.confidence > 0.3

    def test_wide_vibrato(self):
        """Wider vibrato (+/- 80 cents) should still be Kampita."""
        n_frames = 40
        t = np.arange(n_frames) * HOP_MS / 1000.0
        cents = 400.0 + 80.0 * np.sin(2 * np.pi * 4.0 * t)
        segment = _make_segment(cents)
        result = classify_gamaka(segment, hop_ms=HOP_MS)
        assert result.gamaka_type == GamakaType.KAMPITA.value

    def test_fast_vibrato(self):
        """Higher vibrato rate (8 Hz) should still be detected."""
        n_frames = 40
        t = np.arange(n_frames) * HOP_MS / 1000.0
        cents = 300.0 + 30.0 * np.sin(2 * np.pi * 8.0 * t)
        segment = _make_segment(cents)
        result = classify_gamaka(segment, hop_ms=HOP_MS)
        assert result.gamaka_type == GamakaType.KAMPITA.value


class TestJaruDetection:
    """Jaru = smooth glide between two notes."""

    def test_ascending_glide_detected_as_jaru(self):
        """Linear glide from Sa (0 cents) to Ri2 (200 cents) over 300 ms."""
        n_frames = 30  # 300 ms
        cents = np.linspace(0.0, 200.0, n_frames)
        segment = _make_segment(cents)
        result = classify_gamaka(segment, hop_ms=HOP_MS)
        assert result.gamaka_type == GamakaType.JARU.value
        assert result.details["direction"] == "ascending"
        assert result.confidence > 0.4

    def test_descending_glide_detected_as_jaru(self):
        """Descending glide from Pa (700 cents) to Ga3 (400 cents)."""
        n_frames = 30
        cents = np.linspace(700.0, 400.0, n_frames)
        segment = _make_segment(cents)
        result = classify_gamaka(segment, hop_ms=HOP_MS)
        assert result.gamaka_type == GamakaType.JARU.value
        assert result.details["direction"] == "descending"

    def test_small_glide_not_jaru(self):
        """A glide of only 30 cents should not be classified as Jaru."""
        n_frames = 30
        cents = np.linspace(400.0, 430.0, n_frames)
        segment = _make_segment(cents)
        result = classify_gamaka(segment, hop_ms=HOP_MS)
        assert result.gamaka_type != GamakaType.JARU.value


class TestSphurithamDetection:
    """Sphuritham = quick touch of adjacent note then return."""

    def test_brief_spike_detected_as_sphuritham(self):
        """Steady note with a brief 60-cent spike lasting 50 ms."""
        n_frames = 40  # 400 ms total
        cents = np.full(n_frames, 500.0)
        # Insert spike at frames 15-19 (50 ms)
        cents[15:20] = 580.0  # +80 cents spike
        segment = _make_segment(cents)
        result = classify_gamaka(segment, hop_ms=HOP_MS)
        assert result.gamaka_type == GamakaType.SPHURITHAM.value
        assert result.confidence > 0.3

    def test_downward_spike(self):
        """A downward spike (dip) should also be detected as Sphuritham."""
        n_frames = 40
        cents = np.full(n_frames, 700.0)
        cents[10:14] = 630.0  # -70 cents dip for 40 ms
        segment = _make_segment(cents)
        result = classify_gamaka(segment, hop_ms=HOP_MS)
        assert result.gamaka_type == GamakaType.SPHURITHAM.value

    def test_long_spike_not_sphuritham(self):
        """A spike lasting > 100 ms should not be classified as Sphuritham."""
        n_frames = 40
        cents = np.full(n_frames, 500.0)
        # Long spike: frames 10-22 = 130 ms
        cents[10:23] = 600.0
        segment = _make_segment(cents)
        result = classify_gamaka(segment, hop_ms=HOP_MS)
        # Should NOT be sphuritham (spike too long)
        assert result.gamaka_type != GamakaType.SPHURITHAM.value


class TestSteadyDetection:
    """Steady = sustained note with minimal pitch variation."""

    def test_flat_pitch_is_steady(self):
        """A completely flat pitch contour should be classified as steady."""
        n_frames = 30
        cents = np.full(n_frames, 400.0)
        segment = _make_segment(cents)
        result = classify_gamaka(segment, hop_ms=HOP_MS)
        assert result.gamaka_type == GamakaType.STEADY.value
        assert result.confidence > 0.5

    def test_slight_wobble_still_steady(self):
        """Small random variation (< 10 cents) should still be steady."""
        rng = np.random.default_rng(42)
        n_frames = 30
        cents = 500.0 + rng.normal(0, 3, n_frames)  # ~3 cent std dev
        segment = _make_segment(cents)
        result = classify_gamaka(segment, hop_ms=HOP_MS)
        assert result.gamaka_type == GamakaType.STEADY.value

    def test_all_unvoiced_returns_steady(self):
        """A segment with all NaN cents should return steady with 0 confidence."""
        n_frames = 20
        cents = np.full(n_frames, float("nan"))
        freqs = np.zeros(n_frames)
        segment = PitchSegment(
            start_ms=0.0,
            end_ms=(n_frames - 1) * HOP_MS,
            frequencies=freqs,
            reference_sa_hz=REFERENCE_SA_HZ,
            cents_from_sa=cents,
        )
        result = classify_gamaka(segment, hop_ms=HOP_MS)
        assert result.gamaka_type == GamakaType.STEADY.value
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# Integration: segmenter + classifier end-to-end
# ---------------------------------------------------------------------------

class TestSegmenterClassifierIntegration:
    """End-to-end: build a contour, segment it, classify each segment."""

    def test_steady_tone_all_segments_steady(self):
        """A 1-second steady Sa should produce segments all classified as steady."""
        n_frames = 100
        freqs = np.full(n_frames, REFERENCE_SA_HZ)
        contour = _make_contour(freqs)
        segments = segment_contour(
            contour,
            window_ms=300.0,
            hop_ms=100.0,
            reference_sa_hz=REFERENCE_SA_HZ,
        )
        assert len(segments) > 0
        for seg in segments:
            result = classify_gamaka(seg, hop_ms=HOP_MS)
            assert result.gamaka_type == GamakaType.STEADY.value

    def test_vibrato_tone_detected_end_to_end(self):
        """A 1-second vibrato tone should produce segments classified as Kampita."""
        n_frames = 100
        t = np.arange(n_frames) * HOP_MS / 1000.0
        # Vibrato around Pa (392 Hz = Sa * 2^(700/1200))
        pa_hz = REFERENCE_SA_HZ * (2 ** (700.0 / 1200.0))
        freqs = pa_hz * (2 ** (40.0 * np.sin(2 * np.pi * 5.0 * t) / 1200.0))
        contour = _make_contour(freqs)
        segments = segment_contour(
            contour,
            window_ms=300.0,
            hop_ms=100.0,
            reference_sa_hz=REFERENCE_SA_HZ,
        )
        assert len(segments) > 0
        kampita_count = sum(
            1
            for seg in segments
            if classify_gamaka(seg, hop_ms=HOP_MS).gamaka_type
            == GamakaType.KAMPITA.value
        )
        # Most segments should be Kampita
        assert kampita_count >= len(segments) // 2

    def test_glide_tone_detected_end_to_end(self):
        """A 500 ms ascending glide should produce at least one Jaru segment."""
        n_frames = 50  # 500 ms
        sa_cents = 0.0
        ri2_cents = 200.0
        cents = np.linspace(sa_cents, ri2_cents, n_frames)
        freqs = np.array([_cents_to_freq(c) for c in cents])
        contour = _make_contour(freqs)
        segments = segment_contour(
            contour,
            window_ms=300.0,
            hop_ms=100.0,
            reference_sa_hz=REFERENCE_SA_HZ,
        )
        assert len(segments) > 0
        jaru_found = any(
            classify_gamaka(seg, hop_ms=HOP_MS).gamaka_type == GamakaType.JARU.value
            for seg in segments
        )
        assert jaru_found, "Expected at least one segment classified as Jaru"
