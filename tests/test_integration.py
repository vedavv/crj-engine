"""End-to-end integration tests: audio → pitch → swara → raga pipeline."""

import numpy as np
import pytest

from crj_engine.pitch.audio_io import load_audio
from crj_engine.pitch.detector import PitchAlgorithm, PitchContour, PitchFrame, detect_pitch
from crj_engine.pitch.gamaka import GamakaType, classify_gamaka
from crj_engine.pitch.segmenter import segment_contour
from crj_engine.raga.matcher import RagaMatcher
from crj_engine.swara.mapper import freq_to_swara

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REFERENCE_SA_HZ = 261.63  # C4

# Exact frequencies for Shankarabharanam swaras (equal temperament from C4)
SHANKARABHARANAM_FREQS = {
    "Sa": 261.63,
    "Ri2": 293.66,
    "Ga3": 329.63,
    "Ma1": 349.23,
    "Pa": 392.00,
    "Dha2": 440.00,
    "Ni3": 493.88,
}

KALYANI_FREQS = {
    "Sa": 261.63,
    "Ri2": 293.66,
    "Ga3": 329.63,
    "Ma2": 369.99,
    "Pa": 392.00,
    "Dha2": 440.00,
    "Ni3": 493.88,
}


def _generate_tone(freq_hz: float, duration_s: float, sr: int = 16000) -> np.ndarray:
    """Generate a pure sine tone with fade-in/fade-out to avoid transition artifacts."""
    n_samples = int(sr * duration_s)
    t = np.linspace(0, duration_s, n_samples, endpoint=False)
    tone = 0.5 * np.sin(2 * np.pi * freq_hz * t)
    # Apply 20ms fade-in/out to reduce transition artifacts
    fade_samples = min(int(sr * 0.02), n_samples // 4)
    if fade_samples > 0:
        tone[:fade_samples] *= np.linspace(0, 1, fade_samples)
        tone[-fade_samples:] *= np.linspace(1, 0, fade_samples)
    return tone.astype(np.float32)


def _generate_scale(
    freqs: dict[str, float], note_duration: float = 0.5, sr: int = 16000,
) -> np.ndarray:
    """Generate an ascending scale from a dict of swara→freq mappings."""
    segments = []
    for freq in freqs.values():
        segments.append(_generate_tone(freq, note_duration, sr))
    return np.concatenate(segments)


def _stable_swaras(detected_swaras: list[str], min_run: int = 5) -> list[str]:
    """Filter out brief transition artifacts — keep only swaras that appear
    in at least *min_run* consecutive frames, then deduplicate."""
    if not detected_swaras:
        return []

    # Find runs of consecutive identical swaras
    stable = []
    run_start = 0
    for i in range(1, len(detected_swaras)):
        if detected_swaras[i] != detected_swaras[run_start]:
            if i - run_start >= min_run:
                stable.append(detected_swaras[run_start])
            run_start = i
    # Final run
    if len(detected_swaras) - run_start >= min_run:
        stable.append(detected_swaras[run_start])

    # Deduplicate consecutive
    if not stable:
        return []
    deduped = [stable[0]]
    for s in stable[1:]:
        if s != deduped[-1]:
            deduped.append(s)
    return deduped


def _pitch_contour_from_freqs(
    freqs: list[float], hop_ms: float = 10.0
) -> PitchContour:
    """Build a synthetic PitchContour from a list of frequencies."""
    frames = []
    for i, f in enumerate(freqs):
        frames.append(PitchFrame(
            timestamp_ms=i * hop_ms,
            frequency_hz=f,
            confidence=0.95 if f > 0 else 0.0,
        ))
    return PitchContour(
        frames=frames,
        algorithm=PitchAlgorithm.PYIN,
        sample_rate=16000,
        hop_ms=hop_ms,
    )


# ---------------------------------------------------------------------------
# Tests: Audio → Pitch → Swara
# ---------------------------------------------------------------------------

class TestAudioToSwara:
    """Verify the pipeline from synthetic audio through pitch detection to swara mapping."""

    def test_single_sa_tone_maps_correctly(self):
        """A 261.63 Hz tone should map to Sa."""
        audio = _generate_tone(261.63, duration_s=1.0)
        contour = detect_pitch(audio, sr=16000, algorithm=PitchAlgorithm.PYIN)
        voiced = contour.filter_by_confidence(0.3)

        assert len(voiced.frames) > 0

        swara_ids = set()
        for frame in voiced.frames:
            match = freq_to_swara(frame.frequency_hz, reference_sa_hz=REFERENCE_SA_HZ)
            if match:
                swara_ids.add(match.swara_id)

        assert "Sa" in swara_ids

    def test_pa_tone_maps_correctly(self):
        """A 392 Hz tone (Pa) should map to Pa."""
        audio = _generate_tone(392.0, duration_s=1.0)
        contour = detect_pitch(audio, sr=16000, algorithm=PitchAlgorithm.PYIN)
        voiced = contour.filter_by_confidence(0.3)

        assert len(voiced.frames) > 0

        swara_ids = set()
        for frame in voiced.frames:
            match = freq_to_swara(frame.frequency_hz, reference_sa_hz=REFERENCE_SA_HZ)
            if match:
                swara_ids.add(match.swara_id)

        assert "Pa" in swara_ids

    def test_shankarabharanam_scale_detects_multiple_swaras(self):
        """A synthetic Shankarabharanam scale should detect at least 5 distinct swaras."""
        audio = _generate_scale(SHANKARABHARANAM_FREQS, note_duration=0.5)
        contour = detect_pitch(audio, sr=16000, algorithm=PitchAlgorithm.PYIN)
        voiced = contour.filter_by_confidence(0.3)

        swara_ids = set()
        for frame in voiced.frames:
            match = freq_to_swara(frame.frequency_hz, reference_sa_hz=REFERENCE_SA_HZ)
            if match:
                swara_ids.add(match.swara_id)

        # Should detect at least 5 of the 7 swaras (some edge frames may be inaccurate)
        assert len(swara_ids) >= 5, f"Only detected: {swara_ids}"


# ---------------------------------------------------------------------------
# Tests: Swara → Raga
# ---------------------------------------------------------------------------

class TestSwaraToRaga:
    """Verify swara-to-raga identification pipeline."""

    @pytest.fixture
    def matcher(self):
        return RagaMatcher()

    def test_shankarabharanam_identified_from_detected_swaras(self, matcher):
        """Swaras from a Shankarabharanam scale should identify raga 29."""
        # Simulate what the swara mapper would produce from Shankarabharanam audio
        detected = list(SHANKARABHARANAM_FREQS.keys())
        candidates = matcher.identify(detected, top_n=5)

        assert len(candidates) > 0
        assert candidates[0].raga.number == 29
        assert candidates[0].confidence > 0.5

    def test_kalyani_identified_from_detected_swaras(self, matcher):
        """Swaras from a Kalyani scale should identify raga 65."""
        detected = list(KALYANI_FREQS.keys())
        candidates = matcher.identify(detected, top_n=5)

        assert len(candidates) > 0
        assert candidates[0].raga.number == 65

    def test_enharmonic_resolution_after_identification(self, matcher):
        """After raga identification, enharmonic notes should resolve correctly."""
        detected = list(SHANKARABHARANAM_FREQS.keys())
        candidates = matcher.identify(detected, top_n=1)
        raga = candidates[0].raga

        # Position 2 (Ri2/Ga1) should resolve to Ri2 in Shankarabharanam
        assert matcher.resolve_enharmonic(2, raga) == "Ri2"
        # Position 9 (Dha2/Ni1) should resolve to Dha2
        assert matcher.resolve_enharmonic(9, raga) == "Dha2"


# ---------------------------------------------------------------------------
# Tests: Full Pipeline (Audio → Pitch → Swara → Raga)
# ---------------------------------------------------------------------------

class TestFullPipeline:
    """End-to-end: generate audio, detect pitch, map swaras, identify raga."""

    @pytest.fixture
    def matcher(self):
        return RagaMatcher()

    def test_shankarabharanam_end_to_end(self, matcher):
        """Full pipeline should identify Shankarabharanam from synthetic scale audio."""
        # 1. Generate audio
        audio = _generate_scale(SHANKARABHARANAM_FREQS, note_duration=0.5)

        # 2. Detect pitch
        contour = detect_pitch(audio, sr=16000, algorithm=PitchAlgorithm.PYIN)
        voiced = contour.filter_by_confidence(0.3)
        assert len(voiced.frames) > 0

        # 3. Map to swaras
        detected_swaras = []
        for frame in voiced.frames:
            match = freq_to_swara(frame.frequency_hz, reference_sa_hz=REFERENCE_SA_HZ)
            if match:
                detected_swaras.append(match.swara_id)

        assert len(detected_swaras) > 0

        # 4. Filter transition artifacts and deduplicate
        deduped = _stable_swaras(detected_swaras, min_run=5)

        # 5. Identify raga
        candidates = matcher.identify(deduped, top_n=5)
        assert len(candidates) > 0

        # Shankarabharanam (29) should be in top 3
        top_numbers = [c.raga.number for c in candidates[:3]]
        assert 29 in top_numbers, (
            f"Raga 29 not in top 3: "
            f"{[(c.raga.name, c.raga.number) for c in candidates[:3]]}"
        )

    def test_kalyani_end_to_end(self, matcher):
        """Full pipeline should identify Kalyani from synthetic scale audio."""
        audio = _generate_scale(KALYANI_FREQS, note_duration=0.5)
        contour = detect_pitch(audio, sr=16000, algorithm=PitchAlgorithm.PYIN)
        voiced = contour.filter_by_confidence(0.3)

        detected_swaras = []
        for frame in voiced.frames:
            match = freq_to_swara(frame.frequency_hz, reference_sa_hz=REFERENCE_SA_HZ)
            if match:
                detected_swaras.append(match.swara_id)

        # Filter transition artifacts and deduplicate
        deduped = _stable_swaras(detected_swaras, min_run=5)

        candidates = matcher.identify(deduped, top_n=5)
        assert len(candidates) > 0

        top_numbers = [c.raga.number for c in candidates[:3]]
        assert 65 in top_numbers, (
            f"Raga 65 not in top 3: "
            f"{[(c.raga.name, c.raga.number) for c in candidates[:3]]}"
        )


# ---------------------------------------------------------------------------
# Tests: Pitch → Segmenter → Gamaka
# ---------------------------------------------------------------------------

class TestPitchToGamaka:
    """Test gamaka classification from synthetic pitch contours."""

    def test_steady_tone_classified_as_steady(self):
        """A constant pitch should be classified as steady."""
        freqs = [261.63] * 40  # 40 frames × 10ms = 400ms
        contour = _pitch_contour_from_freqs(freqs, hop_ms=10.0)
        segments = segment_contour(
            contour, window_ms=300, hop_ms=100, reference_sa_hz=REFERENCE_SA_HZ
        )

        assert len(segments) > 0
        result = classify_gamaka(segments[0], hop_ms=10.0)
        assert result.gamaka_type == GamakaType.STEADY.value

    def test_vibrato_classified_as_kampita(self):
        """An oscillating pitch should be classified as Kampita."""
        # Generate 600ms of vibrato: 6 Hz oscillation, ±40 cents around Sa (261.63 Hz)
        n_frames = 60
        hop_ms = 10.0
        base_cents = 0.0  # Sa
        vibrato_cents = 40.0
        vibrato_rate = 6.0  # Hz

        cents_values = []
        for i in range(n_frames):
            t = i * hop_ms / 1000.0
            cents_values.append(base_cents + vibrato_cents * np.sin(2 * np.pi * vibrato_rate * t))

        freqs = [REFERENCE_SA_HZ * (2 ** (c / 1200.0)) for c in cents_values]
        contour = _pitch_contour_from_freqs(freqs, hop_ms=hop_ms)
        segments = segment_contour(
            contour, window_ms=500, hop_ms=100, reference_sa_hz=REFERENCE_SA_HZ
        )

        assert len(segments) > 0
        result = classify_gamaka(segments[0], hop_ms=hop_ms)
        assert result.gamaka_type == GamakaType.KAMPITA.value

    def test_glide_classified_as_jaru(self):
        """A smooth ascending glide should be classified as Jaru."""
        # Glide from Sa (0 cents) to Ga3 (400 cents) over 500ms
        n_frames = 50
        hop_ms = 10.0
        cents_values = np.linspace(0, 400, n_frames)
        freqs = [REFERENCE_SA_HZ * (2 ** (c / 1200.0)) for c in cents_values]

        contour = _pitch_contour_from_freqs(freqs, hop_ms=hop_ms)
        segments = segment_contour(
            contour, window_ms=400, hop_ms=100, reference_sa_hz=REFERENCE_SA_HZ
        )

        assert len(segments) > 0
        result = classify_gamaka(segments[0], hop_ms=hop_ms)
        assert result.gamaka_type == GamakaType.JARU.value


# ---------------------------------------------------------------------------
# Tests: WAV file round-trip (if test audio exists)
# ---------------------------------------------------------------------------

class TestWavFilePipeline:
    """Test with actual WAV files generated by generate_test_audio.py."""

    @pytest.fixture
    def test_audio_dir(self):
        from pathlib import Path
        audio_dir = Path(__file__).resolve().parents[1] / "data" / "peer-test" / "audio"
        return audio_dir

    def test_sa_tone_wav_roundtrip(self, test_audio_dir):
        """Load test_sa_261hz.wav and verify it maps to Sa."""
        wav_path = test_audio_dir / "test_sa_261hz.wav"
        if not wav_path.exists():
            pytest.skip("Test audio not generated — run scripts/generate_test_audio.py")

        audio, sr = load_audio(wav_path, target_sr=16000)
        contour = detect_pitch(audio, sr, algorithm=PitchAlgorithm.PYIN)
        voiced = contour.filter_by_confidence(0.3)

        assert len(voiced.frames) > 0
        sa_count = 0
        for frame in voiced.frames:
            match = freq_to_swara(frame.frequency_hz, reference_sa_hz=REFERENCE_SA_HZ)
            if match and match.swara_id == "Sa":
                sa_count += 1

        # At least half of voiced frames should map to Sa
        assert sa_count > len(voiced.frames) * 0.5, (
            f"Only {sa_count}/{len(voiced.frames)} frames mapped to Sa"
        )

    def test_shankarabharanam_wav_to_raga(self, test_audio_dir):
        """Load Shankarabharanam scale WAV and identify the raga."""
        wav_path = test_audio_dir / "test_shankarabharanam_scale.wav"
        if not wav_path.exists():
            pytest.skip("Test audio not generated — run scripts/generate_test_audio.py")

        audio, sr = load_audio(wav_path, target_sr=16000)
        contour = detect_pitch(audio, sr, algorithm=PitchAlgorithm.PYIN)
        voiced = contour.filter_by_confidence(0.3)

        # Map to swaras
        detected_swaras = []
        for frame in voiced.frames:
            match = freq_to_swara(frame.frequency_hz, reference_sa_hz=REFERENCE_SA_HZ)
            if match:
                detected_swaras.append(match.swara_id)

        # Deduplicate
        deduped = [detected_swaras[0]]
        for s in detected_swaras[1:]:
            if s != deduped[-1]:
                deduped.append(s)

        # Identify raga
        matcher = RagaMatcher()
        candidates = matcher.identify(deduped, top_n=5)
        assert len(candidates) > 0

        top_numbers = [c.raga.number for c in candidates[:3]]
        assert 29 in top_numbers, (
            f"Raga 29 not in top 3: "
            f"{[(c.raga.name, c.raga.number) for c in candidates[:3]]}"
        )
