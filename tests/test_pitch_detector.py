"""Tests for pitch detection module using synthetic tones at known frequencies."""

import numpy as np

from crj_engine.pitch.detector import (
    PitchAlgorithm,
    PitchContour,
    detect_pitch,
    detect_pitch_pyin,
)


def _generate_sine(freq_hz: float, duration_s: float = 1.0, sr: int = 16000) -> np.ndarray:
    """Generate a pure sine wave at a known frequency."""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    return np.sin(2 * np.pi * freq_hz * t).astype(np.float32)


class TestPitchDetectionPYIN:
    """Test pYIN detector against synthetic tones."""

    def test_detects_sa_261hz(self):
        audio = _generate_sine(261.63, duration_s=1.0)
        contour = detect_pitch_pyin(audio, sr=16000)
        voiced = contour.filter_by_confidence(0.3)
        assert len(voiced.frames) > 0
        median_freq = np.median(voiced.frequencies)
        assert abs(median_freq - 261.63) < 5.0  # within 5 Hz

    def test_detects_pa_392hz(self):
        audio = _generate_sine(392.0, duration_s=1.0)
        contour = detect_pitch_pyin(audio, sr=16000)
        voiced = contour.filter_by_confidence(0.3)
        assert len(voiced.frames) > 0
        median_freq = np.median(voiced.frequencies)
        assert abs(median_freq - 392.0) < 5.0

    def test_detects_a4_440hz(self):
        audio = _generate_sine(440.0, duration_s=1.0)
        contour = detect_pitch_pyin(audio, sr=16000)
        voiced = contour.filter_by_confidence(0.3)
        assert len(voiced.frames) > 0
        median_freq = np.median(voiced.frequencies)
        assert abs(median_freq - 440.0) < 5.0

    def test_silence_returns_no_voiced(self):
        silence = np.zeros(16000, dtype=np.float32)
        contour = detect_pitch_pyin(silence, sr=16000)
        voiced = contour.filter_by_confidence(0.5)
        assert len(voiced.frames) == 0

    def test_contour_structure(self):
        audio = _generate_sine(300.0, duration_s=0.5)
        contour = detect_pitch_pyin(audio, sr=16000, hop_ms=10.0)
        assert isinstance(contour, PitchContour)
        assert contour.algorithm == PitchAlgorithm.PYIN
        assert contour.sample_rate == 16000
        assert contour.hop_ms == 10.0
        assert len(contour.frames) > 0
        # Timestamps should increment by hop_ms
        if len(contour.frames) > 1:
            dt = contour.frames[1].timestamp_ms - contour.frames[0].timestamp_ms
            assert abs(dt - 10.0) < 0.01

    def test_detect_pitch_dispatcher(self):
        """Test the dispatch function routes to pYIN correctly."""
        audio = _generate_sine(330.0, duration_s=0.5)
        contour = detect_pitch(audio, sr=16000, algorithm=PitchAlgorithm.PYIN)
        assert contour.algorithm == PitchAlgorithm.PYIN
        voiced = contour.filter_by_confidence(0.3)
        assert len(voiced.frames) > 0

    def test_frequency_accuracy_across_range(self):
        """Test detection accuracy across typical vocal range."""
        test_freqs = [200.0, 261.63, 329.63, 440.0, 523.25]
        for expected_freq in test_freqs:
            audio = _generate_sine(expected_freq, duration_s=0.8)
            contour = detect_pitch_pyin(audio, sr=16000)
            voiced = contour.filter_by_confidence(0.3)
            if len(voiced.frames) > 0:
                median_freq = np.median(voiced.frequencies)
                cents_error = abs(1200 * np.log2(median_freq / expected_freq))
                assert cents_error < 20, (
                    f"Frequency {expected_freq} Hz: detected {median_freq:.1f} Hz "
                    f"({cents_error:.1f} cents error)"
                )
