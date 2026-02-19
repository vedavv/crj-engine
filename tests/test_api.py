"""Tests for the CRJ SoundScape API endpoints."""

import io

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from crj_engine.api.main import create_app


@pytest.fixture()
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def sample_wav_bytes():
    """Generate a 2-second 261.63 Hz sine tone as WAV bytes."""
    sr = 16000
    t = np.linspace(0, 2.0, sr * 2, endpoint=False)
    audio = (0.5 * np.sin(2 * np.pi * 261.63 * t)).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV", subtype="FLOAT")
    buf.seek(0)
    return buf.read()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    def test_returns_ok(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "pyin" in data["algorithms"]
        assert "crepe" in data["algorithms"]

    def test_has_version(self, client):
        r = client.get("/api/v1/health")
        assert r.json()["version"] == "0.1.0"


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------


class TestReferenceEndpoints:
    def test_swarasthanas_returns_12(self, client):
        r = client.get("/api/v1/swarasthanas")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 12
        assert data[0]["id"] == "Sa"
        assert "kannada" in data[0]["names"]

    def test_tuning_presets(self, client):
        r = client.get("/api/v1/tuning-presets")
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 4
        ids = [p["id"] for p in data]
        assert "concert_c" in ids

    def test_ragas_returns_72(self, client):
        r = client.get("/api/v1/ragas")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 72
        names = [r["name"] for r in data]
        assert "Dheerasankarabharanam" in names


# ---------------------------------------------------------------------------
# Analyze
# ---------------------------------------------------------------------------


class TestAnalyzeEndpoint:
    def test_analyze_wav_returns_success(self, client, sample_wav_bytes):
        r = client.post(
            "/api/v1/analyze",
            files={"file": ("test.wav", sample_wav_bytes, "audio/wav")},
            data={
                "reference_sa_hz": "261.63",
                "algorithm": "pyin",
                "script": "iast",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "success"
        assert body["algorithm"] == "pyin"
        assert body["script"] == "iast"
        assert body["duration_s"] > 1.0
        assert len(body["notation_iast"]) > 0
        assert len(body["notation_compact"]) > 0
        assert isinstance(body["phrases"], list)
        assert isinstance(body["gamakas"], list)
        assert isinstance(body["raga_candidates"], list)

    def test_analyze_detects_sa(self, client, sample_wav_bytes):
        r = client.post(
            "/api/v1/analyze",
            files={"file": ("test.wav", sample_wav_bytes, "audio/wav")},
            data={"reference_sa_hz": "261.63", "algorithm": "pyin"},
        )
        body = r.json()
        assert "Sa" in body["unique_swaras"]

    def test_analyze_kannada_script(self, client, sample_wav_bytes):
        r = client.post(
            "/api/v1/analyze",
            files={"file": ("test.wav", sample_wav_bytes, "audio/wav")},
            data={"script": "kannada"},
        )
        body = r.json()
        assert body["script"] == "kannada"
        assert len(body["notation_requested"]) > 0

    def test_analyze_includes_contour_when_requested(self, client, sample_wav_bytes):
        r = client.post(
            "/api/v1/analyze",
            files={"file": ("test.wav", sample_wav_bytes, "audio/wav")},
            data={"include_contour": "true"},
        )
        body = r.json()
        assert body["pitch_contour"] is not None
        assert len(body["pitch_contour"]) > 0

    def test_analyze_excludes_contour_by_default(self, client, sample_wav_bytes):
        r = client.post(
            "/api/v1/analyze",
            files={"file": ("test.wav", sample_wav_bytes, "audio/wav")},
        )
        body = r.json()
        assert body["pitch_contour"] is None

    def test_rejects_oversized_file(self, client):
        big = b"\x00" * (11 * 1024 * 1024)
        r = client.post(
            "/api/v1/analyze",
            files={"file": ("big.wav", big, "audio/wav")},
        )
        assert r.status_code == 413

    def test_rejects_unsupported_format(self, client):
        r = client.post(
            "/api/v1/analyze",
            files={"file": ("test.txt", b"not audio", "text/plain")},
        )
        assert r.status_code == 400

    def test_rejects_short_audio(self, client):
        """Audio shorter than 0.5s should be rejected."""
        sr = 16000
        t = np.linspace(0, 0.1, int(sr * 0.1), endpoint=False)
        audio = (0.5 * np.sin(2 * np.pi * 261.63 * t)).astype(np.float32)
        buf = io.BytesIO()
        sf.write(buf, audio, sr, format="WAV", subtype="FLOAT")
        buf.seek(0)

        r = client.post(
            "/api/v1/analyze",
            files={"file": ("short.wav", buf.read(), "audio/wav")},
        )
        assert r.status_code == 400
        assert "too short" in r.json()["detail"].lower()

    def test_phrase_structure(self, client, sample_wav_bytes):
        r = client.post(
            "/api/v1/analyze",
            files={"file": ("test.wav", sample_wav_bytes, "audio/wav")},
        )
        body = r.json()
        for phrase in body["phrases"]:
            assert "notes" in phrase
            assert "start_ms" in phrase
            assert "end_ms" in phrase
            for note in phrase["notes"]:
                assert "swara_id" in note
                assert "octave" in note
                assert "frequency_hz" in note

    def test_raga_candidate_structure(self, client, sample_wav_bytes):
        r = client.post(
            "/api/v1/analyze",
            files={"file": ("test.wav", sample_wav_bytes, "audio/wav")},
        )
        body = r.json()
        for cand in body["raga_candidates"]:
            assert "raga_number" in cand
            assert "raga_name" in cand
            assert "confidence" in cand
            assert "arohana" in cand
