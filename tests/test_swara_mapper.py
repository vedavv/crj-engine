"""Tests for the swara mapper module."""

from crj_engine.swara.mapper import freq_to_swara, freq_to_western


class TestWesternMapping:
    def test_a4_is_a(self):
        note = freq_to_western(440.0)
        assert note.name == "A"
        assert note.octave == 4
        assert abs(note.cents_deviation) < 0.01

    def test_middle_c(self):
        note = freq_to_western(261.63)
        assert note.name == "C"
        assert note.octave == 4

    def test_zero_frequency(self):
        note = freq_to_western(0)
        assert note.name == "—"

    def test_octave_relationship(self):
        note_low = freq_to_western(220.0)
        note_high = freq_to_western(440.0)
        assert note_low.name == note_high.name  # Both A
        assert note_high.octave == note_low.octave + 1


class TestSwaraMapping:
    def test_sa_at_reference(self):
        """Sa frequency should map to Sa."""
        match = freq_to_swara(261.63, reference_sa_hz=261.63)
        assert match is not None
        assert match.swara_id == "Sa"
        assert abs(match.cents_deviation) < 1.0

    def test_pa_perfect_fifth(self):
        """Pa is a perfect fifth above Sa (ratio 3/2)."""
        sa = 261.63
        pa_freq = sa * 3 / 2  # 392.445 Hz
        match = freq_to_swara(pa_freq, reference_sa_hz=sa)
        assert match is not None
        assert match.swara_id == "Pa"

    def test_sa_upper_octave(self):
        """Double the Sa frequency should still map to Sa."""
        sa = 261.63
        match = freq_to_swara(sa * 2, reference_sa_hz=sa)
        assert match is not None
        assert match.swara_id == "Sa"

    def test_out_of_tolerance(self):
        """A frequency far between two swaras should return None with tight tolerance."""
        sa = 261.63
        # Frequency at 50 cents (halfway between Sa and Ri1)
        between_freq = sa * (2 ** (50 / 1200))
        match = freq_to_swara(between_freq, reference_sa_hz=sa, tolerance_cents=10.0)
        assert match is None

    def test_zero_frequency(self):
        match = freq_to_swara(0)
        assert match is None

    def test_multilingual_output(self):
        """Verify all 5 scripts are present in the output."""
        match = freq_to_swara(261.63, reference_sa_hz=261.63)
        assert match is not None
        for script in ["iast", "devanagari", "kannada", "tamil", "telugu"]:
            assert script in match.names

    def test_ri2_ga1_enharmonic(self):
        """Ri2/Ga1 at 200 cents should report aliases."""
        sa = 261.63
        ri2_freq = sa * (2 ** (200 / 1200))
        match = freq_to_swara(ri2_freq, reference_sa_hz=sa)
        assert match is not None
        assert match.swara_id == "Ri2"
        assert "Ga1" in match.aliases
