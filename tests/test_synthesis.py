"""Tests for the audio synthesis / composition rendering module."""

import numpy as np

from crj_engine.synthesis.render import (
    ADSREnvelope,
    ToneType,
    _swara_to_freq,
    generate_tanpura,
    render_bar_audio,
    render_composition,
)
from crj_engine.tala.models import (
    Bar,
    Composition,
    Line,
    Octave,
    SaahityaSyllable,
    Section,
    Speed,
    SwaraNote,
)

REFERENCE_SA_HZ = 261.63


def _note(swara_id: str, octave: Octave = Octave.MADHYA) -> SwaraNote:
    return SwaraNote(swara_id=swara_id, octave=octave)


def _syl(text: str) -> SaahityaSyllable:
    return SaahityaSyllable(text=text)


def _simple_bar(speed: Speed = Speed.PRATAMA) -> Bar:
    """Create a simple Adi tala bar: Sa Ri Ga Ma Pa Dha Ni Sa."""
    n = 8 * speed.value
    cycle = ["Sa", "Ri2", "Ga3", "Ma1", "Pa", "Dha2", "Ni3", "Sa"]
    s_cycle = ["sa", "ri", "ga", "ma", "pa", "dha", "ni", "sa"]

    return Bar(
        tala_id="triputa_chatusra",
        speed=speed,
        swaras=[_note(cycle[i % 8]) for i in range(n)],
        saahitya=[_syl(s_cycle[i % 8]) for i in range(n)],
    )


# ---------------------------------------------------------------------------
# Swara to frequency
# ---------------------------------------------------------------------------

class TestSwaraToFreq:
    def test_sa_madhya(self):
        freq = _swara_to_freq(_note("Sa"), REFERENCE_SA_HZ)
        assert freq is not None
        assert abs(freq - 261.63) < 0.1

    def test_pa_madhya(self):
        freq = _swara_to_freq(_note("Pa"), REFERENCE_SA_HZ)
        assert freq is not None
        # Pa = 700 cents above Sa
        expected = 261.63 * (2 ** (700 / 1200.0))
        assert abs(freq - expected) < 0.1

    def test_sa_mandra(self):
        freq = _swara_to_freq(
            _note("Sa", Octave.MANDRA), REFERENCE_SA_HZ,
        )
        assert freq is not None
        # Mandra Sa = one octave below
        assert abs(freq - 261.63 / 2) < 0.1

    def test_sa_tara(self):
        freq = _swara_to_freq(
            _note("Sa", Octave.TARA), REFERENCE_SA_HZ,
        )
        assert freq is not None
        # Tara Sa = one octave above
        assert abs(freq - 261.63 * 2) < 0.1

    def test_rest_returns_none(self):
        assert _swara_to_freq(_note("-"), REFERENCE_SA_HZ) is None

    def test_sustain_returns_none(self):
        assert _swara_to_freq(_note(","), REFERENCE_SA_HZ) is None


# ---------------------------------------------------------------------------
# ADSR Envelope
# ---------------------------------------------------------------------------

class TestADSREnvelope:
    def test_envelope_starts_at_zero(self):
        env = ADSREnvelope(attack=0.1, decay=0.1, sustain=0.8,
                           release=0.1)
        signal = np.ones(1000, dtype=np.float32)
        result = env.apply(signal)
        assert result[0] < 0.01  # starts near zero

    def test_envelope_ends_at_zero(self):
        env = ADSREnvelope(attack=0.1, decay=0.1, sustain=0.8,
                           release=0.1)
        signal = np.ones(1000, dtype=np.float32)
        result = env.apply(signal)
        assert result[-1] < 0.01  # ends near zero

    def test_envelope_preserves_length(self):
        env = ADSREnvelope()
        signal = np.ones(500, dtype=np.float32)
        result = env.apply(signal)
        assert len(result) == 500


# ---------------------------------------------------------------------------
# Tone generation
# ---------------------------------------------------------------------------

class TestToneGeneration:
    def test_sine_bar_produces_audio(self):
        bar = _simple_bar()
        audio = render_bar_audio(
            bar, REFERENCE_SA_HZ, tempo_bpm=120,
            tone=ToneType.SINE,
        )
        assert len(audio) > 0
        assert audio.dtype == np.float32

    def test_voice_bar_produces_audio(self):
        bar = _simple_bar()
        audio = render_bar_audio(
            bar, REFERENCE_SA_HZ, tempo_bpm=120,
            tone=ToneType.VOICE,
        )
        assert len(audio) > 0

    def test_string_bar_produces_audio(self):
        bar = _simple_bar()
        audio = render_bar_audio(
            bar, REFERENCE_SA_HZ, tempo_bpm=120,
            tone=ToneType.STRING,
        )
        assert len(audio) > 0

    def test_dvitiya_kala_doubles_duration(self):
        bar1 = _simple_bar(Speed.PRATAMA)
        bar2 = _simple_bar(Speed.DVITIYA)
        audio1 = render_bar_audio(
            bar1, REFERENCE_SA_HZ, tempo_bpm=120,
            tone=ToneType.SINE,
        )
        audio2 = render_bar_audio(
            bar2, REFERENCE_SA_HZ, tempo_bpm=120,
            tone=ToneType.SINE,
        )
        # DVITIYA has 16 positions at half duration each = same total
        assert abs(len(audio1) - len(audio2)) < 100

    def test_rest_produces_silence(self):
        bar = Bar(
            tala_id="eka_tisra",
            speed=Speed.PRATAMA,
            swaras=[_note("-"), _note("-"), _note("-")],
            saahitya=[_syl("-"), _syl("-"), _syl("-")],
        )
        audio = render_bar_audio(
            bar, REFERENCE_SA_HZ, tempo_bpm=120,
            tone=ToneType.SINE,
        )
        assert np.max(np.abs(audio)) < 0.001

    def test_sustain_continues_previous_note(self):
        bar = Bar(
            tala_id="eka_tisra",
            speed=Speed.PRATAMA,
            swaras=[_note("Sa"), _note(","), _note(",")],
            saahitya=[_syl("sa"), _syl("-"), _syl("-")],
        )
        audio = render_bar_audio(
            bar, REFERENCE_SA_HZ, tempo_bpm=120,
            tone=ToneType.SINE,
        )
        # Should have audio throughout (not silence in sustain)
        third = len(audio) // 3
        assert np.max(np.abs(audio[third:2*third])) > 0.1

    def test_audio_not_clipping(self):
        bar = _simple_bar()
        audio = render_bar_audio(
            bar, REFERENCE_SA_HZ, tempo_bpm=120,
            tone=ToneType.VOICE,
        )
        assert np.max(np.abs(audio)) <= 1.0


# ---------------------------------------------------------------------------
# Tanpura
# ---------------------------------------------------------------------------

class TestTanpura:
    def test_tanpura_duration(self):
        audio = generate_tanpura(
            REFERENCE_SA_HZ, duration_s=5.0, sr=44100,
        )
        expected_samples = int(44100 * 5.0)
        assert len(audio) == expected_samples

    def test_tanpura_not_silent(self):
        audio = generate_tanpura(REFERENCE_SA_HZ, duration_s=2.0)
        assert np.max(np.abs(audio)) > 0.1

    def test_tanpura_not_clipping(self):
        audio = generate_tanpura(REFERENCE_SA_HZ, duration_s=2.0)
        assert np.max(np.abs(audio)) <= 1.0


# ---------------------------------------------------------------------------
# Full composition rendering
# ---------------------------------------------------------------------------

class TestCompositionRendering:
    def _make_composition(self) -> Composition:
        bar = _simple_bar()
        line = Line(bars=[bar, bar], repeat=2)
        section = Section(name="pallavi", lines=[line])
        return Composition(
            title="Test",
            raga="Shankarabharanam",
            tala_id="triputa_chatusra",
            composer="Test",
            reference_sa_hz=REFERENCE_SA_HZ,
            sections=[section],
        )

    def test_renders_without_tanpura(self):
        comp = self._make_composition()
        audio = render_composition(
            comp, tempo_bpm=120, tone=ToneType.SINE,
            include_tanpura=False,
        )
        assert len(audio) > 0
        assert audio.dtype == np.float32

    def test_renders_with_tanpura(self):
        comp = self._make_composition()
        audio = render_composition(
            comp, tempo_bpm=120, tone=ToneType.SINE,
            include_tanpura=True,
        )
        assert len(audio) > 0

    def test_repeat_doubles_length(self):
        bar = _simple_bar()
        line1 = Line(bars=[bar], repeat=1)
        line2 = Line(bars=[bar], repeat=2)

        comp1 = Composition(
            title="T", raga="R", tala_id="triputa_chatusra",
            composer="C", reference_sa_hz=REFERENCE_SA_HZ,
            sections=[Section("p", [line1])],
        )
        comp2 = Composition(
            title="T", raga="R", tala_id="triputa_chatusra",
            composer="C", reference_sa_hz=REFERENCE_SA_HZ,
            sections=[Section("p", [line2])],
        )

        a1 = render_composition(
            comp1, tone=ToneType.SINE, include_tanpura=False,
        )
        a2 = render_composition(
            comp2, tone=ToneType.SINE, include_tanpura=False,
        )
        assert abs(len(a2) - 2 * len(a1)) < 100

    def test_with_tanpura_not_clipping(self):
        comp = self._make_composition()
        audio = render_composition(
            comp, tempo_bpm=120, tone=ToneType.VOICE,
            include_tanpura=True,
        )
        assert np.max(np.abs(audio)) <= 1.0
