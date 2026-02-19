"""Tests for rule-based raga identification."""

import pytest

from crj_engine.raga.matcher import RagaMatcher


@pytest.fixture
def matcher():
    return RagaMatcher()


class TestRagaDatabase:
    def test_loads_72_ragas(self, matcher):
        assert len(matcher.ragas) == 72

    def test_first_raga_is_kanakangi(self, matcher):
        raga = matcher.ragas[0]
        assert raga.number == 1
        assert raga.name == "Kanakangi"
        assert raga.ma_type == "shuddha"

    def test_last_raga_is_rasikapriya(self, matcher):
        raga = matcher.ragas[-1]
        assert raga.number == 72
        assert raga.name == "Rasikapriya"
        assert raga.ma_type == "prati"

    def test_shankarabharanam_is_29(self, matcher):
        raga = matcher.get_raga_by_number(29)
        assert raga is not None
        assert raga.name == "Dheerasankarabharanam"
        assert raga.arohana == ["Sa", "Ri2", "Ga3", "Ma1", "Pa", "Dha2", "Ni3", "Sa"]
        assert raga.ma_type == "shuddha"

    def test_kalyani_is_65(self, matcher):
        raga = matcher.get_raga_by_number(65)
        assert raga is not None
        assert raga.name == "Mechakalyani"
        assert raga.ma_type == "prati"
        assert "Ma2" in raga.arohana

    def test_lookup_by_alias(self, matcher):
        raga = matcher.get_raga_by_name("Kalyani")
        assert raga is not None
        assert raga.number == 65

    def test_lookup_case_insensitive(self, matcher):
        raga = matcher.get_raga_by_name("shankarabharanam")
        assert raga is not None
        assert raga.number == 29

    def test_ma1_ragas_are_1_to_36(self, matcher):
        for raga in matcher.ragas:
            if raga.number <= 36:
                assert raga.ma_type == "shuddha", f"Raga {raga.number} should be shuddha"
                assert "Ma1" in raga.arohana
            else:
                assert raga.ma_type == "prati", f"Raga {raga.number} should be prati"
                assert "Ma2" in raga.arohana


class TestRagaIdentification:
    def test_shankarabharanam_from_full_scale(self, matcher):
        """The major scale swaras should identify as Shankarabharanam."""
        swaras = ["Sa", "Ri2", "Ga3", "Ma1", "Pa", "Dha2", "Ni3", "Sa"]
        candidates = matcher.identify(swaras, top_n=5)
        assert len(candidates) > 0
        assert candidates[0].raga.number == 29

    def test_mayamalavagowla_from_scale(self, matcher):
        """Raga 15: Sa Ri1 Ga3 Ma1 Pa Dha1 Ni3."""
        swaras = ["Sa", "Ri1", "Ga3", "Ma1", "Pa", "Dha1", "Ni3", "Sa"]
        candidates = matcher.identify(swaras, top_n=5)
        assert len(candidates) > 0
        assert candidates[0].raga.number == 15

    def test_todi_from_scale(self, matcher):
        """Raga 8 (Hanumatodi): Sa Ri1 Ga2 Ma1 Pa Dha1 Ni2."""
        swaras = ["Sa", "Ri1", "Ga2", "Ma1", "Pa", "Dha1", "Ni2", "Sa"]
        candidates = matcher.identify(swaras, top_n=5)
        assert len(candidates) > 0
        assert candidates[0].raga.number == 8

    def test_kalyani_uses_ma2(self, matcher):
        """Raga 65 (Mechakalyani): Sa Ri2 Ga3 Ma2 Pa Dha2 Ni3."""
        swaras = ["Sa", "Ri2", "Ga3", "Ma2", "Pa", "Dha2", "Ni3", "Sa"]
        candidates = matcher.identify(swaras, top_n=5)
        assert len(candidates) > 0
        assert candidates[0].raga.number == 65

    def test_partial_scale_still_identifies(self, matcher):
        """Even with a few swaras, the right raga should rank high."""
        swaras = ["Sa", "Ga3", "Pa", "Dha2", "Ni3"]
        candidates = matcher.identify(swaras, top_n=10)
        assert len(candidates) > 0
        # Shankarabharanam (29) or Kalyani (65) should be in top results
        top_numbers = [c.raga.number for c in candidates]
        assert 29 in top_numbers or 65 in top_numbers

    def test_empty_input_returns_empty(self, matcher):
        assert matcher.identify([]) == []

    def test_confidence_is_bounded(self, matcher):
        swaras = ["Sa", "Ri2", "Ga3", "Ma1", "Pa", "Dha2", "Ni3"]
        candidates = matcher.identify(swaras)
        for c in candidates:
            assert 0.0 <= c.confidence <= 1.0


class TestEnharmonicResolution:
    def test_ri2_in_shankarabharanam(self, matcher):
        raga = matcher.get_raga_by_number(29)
        resolved = matcher.resolve_enharmonic(2, raga)  # position 2 = Ri2/Ga1
        assert resolved == "Ri2"

    def test_ga1_in_kanakangi(self, matcher):
        raga = matcher.get_raga_by_number(1)
        resolved = matcher.resolve_enharmonic(2, raga)  # position 2 = Ri2/Ga1
        assert resolved == "Ga1"

    def test_fixed_notes_resolve_uniquely(self, matcher):
        raga = matcher.get_raga_by_number(29)
        assert matcher.resolve_enharmonic(0, raga) == "Sa"
        assert matcher.resolve_enharmonic(7, raga) == "Pa"
