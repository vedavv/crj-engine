"""Tests for tala engine (percussion synthesis + loop rendering + endpoint)."""

from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from crj_engine.api.main import create_app
from crj_engine.synthesis.percussion import (
    list_instruments,
    list_strokes,
    synthesize_stroke,
)
from crj_engine.synthesis.tala_engine import (
    get_pattern,
    list_pattern_keys,
    render_tala_loop,
)
from crj_engine.tala.models import load_tala_db


@pytest.fixture
def client():
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# Percussion stroke synthesis
# ---------------------------------------------------------------------------


class TestPercussion:
    def test_all_instruments_have_strokes(self):
        for instrument in list_instruments():
            strokes = list_strokes(instrument)
            assert len(strokes) >= 3

    def test_synthesize_returns_nonzero_audio(self):
        for instrument in list_instruments():
            for stroke in list_strokes(instrument):
                audio = synthesize_stroke(instrument, stroke)
                assert len(audio) > 0
                assert audio.dtype == np.float32
                assert np.max(np.abs(audio)) > 0.1

    def test_unknown_stroke_raises(self):
        with pytest.raises(ValueError):
            synthesize_stroke("tabla", "nonexistent_stroke")

    def test_unknown_instrument_raises(self):
        with pytest.raises(ValueError):
            synthesize_stroke("nonexistent_instrument", "ta")

    def test_caching_returns_consistent_results(self):
        a = synthesize_stroke("tabla", "dha")
        b = synthesize_stroke("tabla", "dha")
        # Both copies; same content
        assert np.allclose(a, b)


# ---------------------------------------------------------------------------
# Tala engine
# ---------------------------------------------------------------------------


class TestTalaEngine:
    def test_carnatic_adi_pattern_exists(self):
        p = get_pattern("triputa_chatusra", "mridangam")
        assert len(p.strokes) == 8
        assert p.accents[0] == 2  # sam

    def test_teentaal_pattern_exists(self):
        p = get_pattern("teentaal", "tabla")
        assert len(p.strokes) == 16
        assert p.accents[0] == 2  # sam
        # Vibhag 3 (beats 9-12) is khali in Teentaal
        assert p.accents[8] == 0
        assert p.accents[11] == 0

    def test_chautal_pakhavaj(self):
        p = get_pattern("chautal", "pakhavaj")
        assert len(p.strokes) == 12
        assert p.accents[0] == 2

    def test_unknown_tala_falls_back(self):
        # Returns a click-style pattern when the requested combination isn't
        # registered — no crash.
        with pytest.raises(KeyError):
            get_pattern("totally_invented_tala", "mridangam")

    def test_pattern_lengths_match_tala_aksharas(self):
        db = load_tala_db()
        for (tala_id, instrument), _ in zip(list_pattern_keys(), list_pattern_keys()):
            tala = db[tala_id]
            pattern = get_pattern(tala_id, instrument)
            assert len(pattern.strokes) == tala.total_aksharas, (
                f"{tala_id}/{instrument}: pattern has {len(pattern.strokes)} "
                f"strokes but tala expects {tala.total_aksharas} matras"
            )
            assert len(pattern.accents) == tala.total_aksharas

    def test_render_loop_basic(self):
        audio = render_tala_loop(
            tala_id="triputa_chatusra",
            instrument="mridangam",
            tempo_bpm=80,
            num_cycles=2,
            sr=22050,
        )
        # 8 matras at 80 BPM = 6 sec per cycle, 12s for 2 cycles + ~0.75s tail
        assert len(audio) > int(22050 * 6)
        assert len(audio) < int(22050 * 14)
        assert audio.dtype == np.float32
        # Should have meaningful audio content
        assert np.max(np.abs(audio)) > 0.1

    def test_render_invalid_tempo(self):
        with pytest.raises(ValueError):
            render_tala_loop("triputa_chatusra", tempo_bpm=10)
        with pytest.raises(ValueError):
            render_tala_loop("triputa_chatusra", tempo_bpm=400)

    def test_render_invalid_instrument(self):
        with pytest.raises(ValueError):
            render_tala_loop("triputa_chatusra", instrument="violin")


# ---------------------------------------------------------------------------
# /api/v1/tala-loop endpoint
# ---------------------------------------------------------------------------


class TestTalaLoopEndpoint:
    def test_returns_wav_for_carnatic(self, client):
        r = client.get(
            "/api/v1/tala-loop",
            params={
                "tala_id": "triputa_chatusra",
                "instrument": "mridangam",
                "tempo_bpm": 80,
                "num_cycles": 2,
            },
        )
        assert r.status_code == 200
        assert r.headers["content-type"] == "audio/wav"
        assert r.content[:4] == b"RIFF"
        assert "max-age" in r.headers.get("cache-control", "").lower()

    def test_returns_wav_for_hindustani(self, client):
        r = client.get(
            "/api/v1/tala-loop",
            params={
                "tala_id": "teentaal",
                "instrument": "tabla",
                "tempo_bpm": 100,
                "num_cycles": 1,
            },
        )
        assert r.status_code == 200
        assert r.content[:4] == b"RIFF"

    def test_returns_wav_for_dhrupad(self, client):
        r = client.get(
            "/api/v1/tala-loop",
            params={
                "tala_id": "chautal",
                "instrument": "pakhavaj",
                "tempo_bpm": 60,
                "num_cycles": 1,
            },
        )
        assert r.status_code == 200
        assert r.content[:4] == b"RIFF"

    def test_unknown_tala_returns_404(self, client):
        r = client.get(
            "/api/v1/tala-loop",
            params={
                "tala_id": "made_up",
                "instrument": "tabla",
            },
        )
        assert r.status_code == 404

    def test_invalid_instrument_rejected(self, client):
        r = client.get(
            "/api/v1/tala-loop",
            params={
                "tala_id": "teentaal",
                "instrument": "saxophone",
            },
        )
        assert r.status_code == 422

    def test_tala_pattern_endpoint(self, client):
        r = client.get(
            "/api/v1/tala-pattern",
            params={"tala_id": "teentaal", "instrument": "tabla"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["tala_id"] == "teentaal"
        assert body["instrument"] == "tabla"
        assert len(body["strokes"]) == 16


# ---------------------------------------------------------------------------
# Tala DB merging (Stage 6)
# ---------------------------------------------------------------------------


class TestTalaDbMerge:
    def test_loads_all_traditions(self, client):
        r = client.get("/api/v1/talas")
        assert r.status_code == 200
        data = r.json()
        traditions = {t["tradition"] for t in data}
        assert "carnatic" in traditions
        assert "hindustani" in traditions
        assert "dhrupad" in traditions

    def test_filter_by_tradition(self, client):
        r = client.get("/api/v1/talas", params={"tradition": "hindustani"})
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 3  # Teentaal, Ektaal, Dadra
        for t in data:
            assert t["tradition"] == "hindustani"
        ids = {t["id"] for t in data}
        assert {"teentaal", "ektaal", "dadra"} == ids

    def test_hindustani_includes_vibhag_marks(self, client):
        r = client.get("/api/v1/talas", params={"tradition": "hindustani"})
        teentaal = next(t for t in r.json() if t["id"] == "teentaal")
        assert teentaal["vibhag_marks"] == ["sam", "tali", "khali", "tali"]

    def test_ektaal_jati_count_uses_json_override(self, client):
        # Ektaal's vibhags are 2 matras each (the jati_count_override in
        # hindustani.json). Without the override, jati=chatusra would yield 4
        # which is wrong for Ektaal's vibhag structure.
        r = client.get("/api/v1/talas", params={"tradition": "hindustani"})
        ektaal = next(t for t in r.json() if t["id"] == "ektaal")
        assert ektaal["jati_count"] == 2

    def test_carnatic_jati_count_uses_enum(self, client):
        # Carnatic talas have no jati_count override in JSON, so the API
        # value should still be the Jati enum value.
        r = client.get("/api/v1/talas", params={"tradition": "carnatic"})
        adi = next(t for t in r.json() if t["id"] == "triputa_chatusra")
        assert adi["jati_count"] == 4  # CHATUSRA
