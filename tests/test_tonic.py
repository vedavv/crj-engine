"""Tests for Sa (tonic) detection."""

from __future__ import annotations

import io

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from crj_engine.api.main import create_app
from crj_engine.pitch.tonic import _hz_to_western, detect_tonic

SR = 16000


def _synth_drone_with_overtones(
    sa_hz: float, duration_s: float = 8.0, sr: int = SR, with_pa: bool = True
) -> np.ndarray:
    """Synthesise a Sa-dominated tone with optional Pa partner.

    Strong, sustained Sa with a few harmonics — close enough to a vocal Sa
    drone to exercise the histogram detector. With Pa enabled we mimic a
    tanpura: Sa + Pa(700 cents) reinforces the perfect-fifth heuristic.
    """
    n = int(duration_s * sr)
    t = np.linspace(0, duration_s, n, endpoint=False)
    audio = np.zeros(n, dtype=np.float64)

    # Sa fundamental + harmonics
    for h, w in [(1, 1.0), (2, 0.5), (3, 0.25), (4, 0.12)]:
        audio += w * np.sin(2 * np.pi * sa_hz * h * t)

    if with_pa:
        pa_hz = sa_hz * (2 ** (700 / 1200.0))
        for h, w in [(1, 0.7), (2, 0.3), (3, 0.15)]:
            audio += w * np.sin(2 * np.pi * pa_hz * h * t)

    audio /= np.max(np.abs(audio))
    return audio.astype(np.float32) * 0.5


@pytest.fixture
def client():
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# Pure algorithm tests
# ---------------------------------------------------------------------------


class TestHzToWestern:
    def test_a4(self):
        assert _hz_to_western(440.0) == "A4"

    def test_c4(self):
        assert _hz_to_western(261.63) == "C4"

    def test_d_sharp_4(self):
        assert _hz_to_western(311.13) == "D#4"

    def test_zero_hz(self):
        assert _hz_to_western(0.0) == "?"


class TestDetectTonic:
    def test_detects_c4_with_pa(self):
        audio = _synth_drone_with_overtones(261.63, duration_s=6.0, with_pa=True)
        result = detect_tonic(audio, sr=SR)
        # Allow 30-cent tolerance — synthesis rounding + histogram bin width
        assert abs(result.suggested_sa_hz - 261.63) / 261.63 < 0.02
        assert result.western_label == "C4"
        assert result.confidence > 0.3
        assert any(c.has_perfect_fifth for c in result.candidates)

    def test_detects_a3(self):
        audio = _synth_drone_with_overtones(220.0, duration_s=6.0, with_pa=True)
        result = detect_tonic(audio, sr=SR)
        assert abs(result.suggested_sa_hz - 220.0) / 220.0 < 0.02
        assert result.western_label == "A3"

    def test_detects_d_sharp_4(self):
        audio = _synth_drone_with_overtones(311.13, duration_s=6.0, with_pa=True)
        result = detect_tonic(audio, sr=SR)
        assert abs(result.suggested_sa_hz - 311.13) / 311.13 < 0.02
        assert result.western_label == "D#4"

    def test_returns_zero_confidence_for_silence(self):
        silence = np.zeros(int(3.0 * SR), dtype=np.float32)
        result = detect_tonic(silence, sr=SR)
        assert result.confidence == 0.0
        assert result.candidates == []

    def test_top_candidates_returned(self):
        audio = _synth_drone_with_overtones(261.63, duration_s=6.0, with_pa=True)
        result = detect_tonic(audio, sr=SR, top_n=3)
        assert len(result.candidates) >= 1
        assert len(result.candidates) <= 3
        # All candidates must be in vocal Sa range
        for c in result.candidates:
            assert 80.0 <= c.sa_hz <= 440.0


# ---------------------------------------------------------------------------
# /api/v1/detect-sa endpoint tests
# ---------------------------------------------------------------------------


class TestDetectSaEndpoint:
    def test_detects_c4_via_api(self, client):
        audio = _synth_drone_with_overtones(261.63, duration_s=6.0, with_pa=True)
        buf = io.BytesIO()
        sf.write(buf, audio, SR, format="WAV", subtype="PCM_16")
        buf.seek(0)

        r = client.post(
            "/api/v1/detect-sa",
            files={"file": ("clip.wav", buf.read(), "audio/wav")},
        )
        assert r.status_code == 200
        body = r.json()
        assert "suggested_sa_hz" in body
        assert "western_label" in body
        assert "candidates" in body
        assert abs(body["suggested_sa_hz"] - 261.63) / 261.63 < 0.02
        assert body["western_label"] == "C4"

    def test_rejects_too_short_clip(self, client):
        audio = np.zeros(int(0.3 * SR), dtype=np.float32)
        buf = io.BytesIO()
        sf.write(buf, audio, SR, format="WAV", subtype="PCM_16")
        buf.seek(0)
        r = client.post(
            "/api/v1/detect-sa",
            files={"file": ("tiny.wav", buf.read(), "audio/wav")},
        )
        assert r.status_code == 400

    def test_rejects_unsupported_format(self, client):
        r = client.post(
            "/api/v1/detect-sa",
            files={"file": ("a.txt", b"not audio", "text/plain")},
        )
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# /api/v1/shruti endpoint tests
# ---------------------------------------------------------------------------


class TestShrutiEndpoint:
    def test_returns_wav_for_sa_pa(self, client):
        r = client.get("/api/v1/shruti", params={"sa_hz": 261.63, "pattern": "sa_pa"})
        assert r.status_code == 200
        assert r.headers["content-type"] == "audio/wav"
        assert r.content[:4] == b"RIFF"

    def test_returns_wav_for_sa_ma(self, client):
        r = client.get("/api/v1/shruti", params={"sa_hz": 261.63, "pattern": "sa_ma"})
        assert r.status_code == 200
        assert r.content[:4] == b"RIFF"

    def test_returns_wav_for_sa_ni(self, client):
        r = client.get("/api/v1/shruti", params={"sa_hz": 261.63, "pattern": "sa_ni"})
        assert r.status_code == 200
        assert r.content[:4] == b"RIFF"

    def test_rejects_invalid_pattern(self, client):
        r = client.get(
            "/api/v1/shruti", params={"sa_hz": 261.63, "pattern": "invalid"}
        )
        assert r.status_code == 422  # FastAPI Query regex rejection

    def test_rejects_out_of_range_hz(self, client):
        r = client.get("/api/v1/shruti", params={"sa_hz": 5000.0, "pattern": "sa_pa"})
        assert r.status_code == 422

    def test_cache_header_set(self, client):
        r = client.get("/api/v1/shruti", params={"sa_hz": 261.63, "pattern": "sa_pa"})
        assert r.status_code == 200
        assert "max-age" in r.headers.get("cache-control", "").lower()
