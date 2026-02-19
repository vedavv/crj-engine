"""Tests for the tala composition and notation module."""

import json
import tempfile
from pathlib import Path

import pytest

from crj_engine.tala.models import (
    Bar,
    Composition,
    Jati,
    Line,
    Octave,
    SaahityaSyllable,
    Section,
    Speed,
    SwaraNote,
    get_tala,
    load_tala_db,
)
from crj_engine.tala.notation import (
    render_bar,
    render_bar_saahitya,
    render_bar_swaras,
    render_swara,
)
from crj_engine.tala.serializer import (
    composition_from_dict,
    composition_to_dict,
    load_composition,
    save_composition,
)

# ---------------------------------------------------------------------------
# Tala Database
# ---------------------------------------------------------------------------

class TestTalaDatabase:
    def test_loads_35_talas(self):
        db = load_tala_db()
        assert len(db) == 35

    def test_adi_tala_is_triputa_chatusra(self):
        tala = get_tala("triputa_chatusra")
        assert tala.name == "Triputa Tala (Chatusra)"
        assert tala.base_tala == "Triputa"
        assert tala.jati == Jati.CHATUSRA
        assert tala.total_aksharas == 8
        assert tala.beat_pattern == [4, 2, 2]
        assert tala.components == ["laghu", "drutam", "drutam"]

    def test_adi_tala_by_alias(self):
        tala = get_tala("Adi Tala")
        assert tala.id == "triputa_chatusra"

    def test_rupaka_tala(self):
        tala = get_tala("rupaka_chatusra")
        assert tala.total_aksharas == 6
        assert tala.beat_pattern == [2, 4]
        assert tala.components == ["drutam", "laghu"]

    def test_eka_tala(self):
        tala = get_tala("eka_chatusra")
        assert tala.total_aksharas == 4
        assert tala.components == ["laghu"]

    def test_jhampa_misra(self):
        tala = get_tala("jhampa_misra")
        assert tala.total_aksharas == 10
        assert tala.components == ["laghu", "anudrutam", "drutam"]
        assert tala.beat_pattern == [7, 1, 2]

    def test_all_aksharas_match_beat_pattern_sum(self):
        db = load_tala_db()
        for tala in db.values():
            assert tala.total_aksharas == sum(tala.beat_pattern), (
                f"{tala.id}: total_aksharas ({tala.total_aksharas}) "
                f"!= sum(beat_pattern) ({sum(tala.beat_pattern)})"
            )

    def test_unknown_tala_raises(self):
        with pytest.raises(KeyError):
            get_tala("nonexistent_tala")

    def test_7_base_talas_present(self):
        db = load_tala_db()
        base_talas = {t.base_tala for t in db.values()}
        expected = {
            "Eka", "Rupaka", "Triputa",
            "Matya", "Jhampa", "Dhruva", "Ata",
        }
        assert base_talas == expected

    def test_5_jatis_per_base_tala(self):
        db = load_tala_db()
        base_groups: dict[str, set] = {}
        for tala in db.values():
            base_groups.setdefault(tala.base_tala, set()).add(tala.jati)
        for base, jatis in base_groups.items():
            assert len(jatis) == 5, (
                f"{base} has {len(jatis)} jatis, expected 5"
            )


# ---------------------------------------------------------------------------
# Octave Notation
# ---------------------------------------------------------------------------

class TestOctaveNotation:
    def test_madhya_no_mark(self):
        note = SwaraNote(swara_id="Sa", octave=Octave.MADHYA)
        rendered = render_swara(note, script="iast")
        assert rendered == "Sa"

    def test_mandra_dot_below(self):
        note = SwaraNote(swara_id="Sa", octave=Octave.MANDRA)
        rendered = render_swara(note, script="iast")
        # Should have combining dot below after first char
        assert "\u0323" in rendered
        assert rendered == "S\u0323a"

    def test_tara_dot_above(self):
        note = SwaraNote(swara_id="Sa", octave=Octave.TARA)
        rendered = render_swara(note, script="iast")
        assert "\u0307" in rendered
        assert rendered == "S\u0307a"

    def test_rest_passes_through(self):
        note = SwaraNote(swara_id="-", octave=Octave.MADHYA)
        assert render_swara(note) == "-"

    def test_sustain_passes_through(self):
        note = SwaraNote(swara_id=",", octave=Octave.MADHYA)
        assert render_swara(note) == ","

    def test_kannada_script(self):
        note = SwaraNote(swara_id="Sa", octave=Octave.MADHYA)
        rendered = render_swara(note, script="kannada")
        # Should return the Kannada character for Sa
        assert rendered != "Sa"  # Should be in Kannada
        assert len(rendered) > 0

    def test_pa_with_octave_marks(self):
        pa_mandra = SwaraNote(swara_id="Pa", octave=Octave.MANDRA)
        pa_madhya = SwaraNote(swara_id="Pa", octave=Octave.MADHYA)
        pa_tara = SwaraNote(swara_id="Pa", octave=Octave.TARA)

        r_mandra = render_swara(pa_mandra)
        r_madhya = render_swara(pa_madhya)
        r_tara = render_swara(pa_tara)

        # Madhya should be unmarked
        assert "\u0323" not in r_madhya
        assert "\u0307" not in r_madhya
        # Mandra should have dot below
        assert "\u0323" in r_mandra
        # Tara should have dot above
        assert "\u0307" in r_tara


# ---------------------------------------------------------------------------
# Bar and Composition Model
# ---------------------------------------------------------------------------

def _make_adi_bar(
    speed: Speed = Speed.PRATAMA,
) -> Bar:
    """Helper: create a simple Adi tala bar in Shankarabharanam."""
    n = 8 * speed.value
    swaras_cycle = ["Sa", "Ri2", "Ga3", "Ma1", "Pa", "Dha2", "Ni3", "Sa"]
    saahitya_cycle = ["sa", "ri", "ga", "ma", "pa", "dha", "ni", "sa"]

    swaras = []
    saahitya = []
    for i in range(n):
        idx = i % len(swaras_cycle)
        swaras.append(SwaraNote(swara_id=swaras_cycle[idx]))
        saahitya.append(SaahityaSyllable(text=saahitya_cycle[idx]))

    return Bar(
        tala_id="triputa_chatusra",
        speed=speed,
        swaras=swaras,
        saahitya=saahitya,
    )


class TestBarModel:
    def test_pratama_kala_8_positions(self):
        bar = _make_adi_bar(Speed.PRATAMA)
        assert bar.num_positions == 8

    def test_dvitiya_kala_16_positions(self):
        bar = _make_adi_bar(Speed.DVITIYA)
        assert bar.num_positions == 16

    def test_tritiya_kala_24_positions(self):
        bar = _make_adi_bar(Speed.TRITIYA)
        assert bar.num_positions == 24

    def test_validate_passes_for_correct_bar(self):
        bar = _make_adi_bar()
        db = load_tala_db()
        bar.validate(db)  # should not raise

    def test_validate_fails_mismatched_lengths(self):
        bar = _make_adi_bar()
        bar.saahitya = bar.saahitya[:-1]  # remove one
        with pytest.raises(ValueError, match="1:1 aligned"):
            bar.validate()

    def test_validate_fails_wrong_position_count(self):
        bar = _make_adi_bar()
        bar.swaras.append(SwaraNote(swara_id="Sa"))
        bar.saahitya.append(SaahityaSyllable(text="sa"))
        db = load_tala_db()
        with pytest.raises(ValueError, match="expects 8"):
            bar.validate(db)


class TestCompositionModel:
    def test_basic_composition_structure(self):
        bar = _make_adi_bar()
        line = Line(bars=[bar, bar, bar, bar], repeat=2)
        section = Section(name="pallavi", lines=[line])
        comp = Composition(
            title="Test Varnam",
            raga="Shankarabharanam",
            tala_id="triputa_chatusra",
            composer="Test Composer",
            reference_sa_hz=261.63,
            sections=[section],
        )
        assert comp.title == "Test Varnam"
        assert len(comp.sections) == 1
        assert len(comp.sections[0].lines) == 1
        assert len(comp.sections[0].lines[0].bars) == 4
        assert comp.sections[0].lines[0].repeat == 2


# ---------------------------------------------------------------------------
# Bar Rendering
# ---------------------------------------------------------------------------

class TestBarRendering:
    def test_render_bar_swaras(self):
        bar = _make_adi_bar()
        rendered = render_bar_swaras(bar)
        assert "Sa" in rendered
        assert "Pa" in rendered

    def test_render_bar_saahitya(self):
        bar = _make_adi_bar()
        rendered = render_bar_saahitya(bar)
        assert "sa" in rendered
        assert "pa" in rendered

    def test_render_bar_two_lines(self):
        bar = _make_adi_bar()
        rendered = render_bar(bar)
        lines = rendered.split("\n")
        assert len(lines) == 2

    def test_render_with_octave_marks(self):
        swaras = [
            SwaraNote("Sa", Octave.MANDRA),
            SwaraNote("Pa", Octave.MADHYA),
            SwaraNote("Sa", Octave.TARA),
        ]
        saahitya = [
            SaahityaSyllable("lo"),
            SaahityaSyllable("mid"),
            SaahityaSyllable("hi"),
        ]
        bar = Bar(
            tala_id="eka_tisra",
            speed=Speed.PRATAMA,
            swaras=swaras,
            saahitya=saahitya,
        )
        rendered = render_bar_swaras(bar)
        # Mandra Sa should have dot below
        assert "\u0323" in rendered
        # Tara Sa should have dot above
        assert "\u0307" in rendered


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

class TestSerialization:
    def _make_test_composition(self) -> Composition:
        bar1 = _make_adi_bar(Speed.PRATAMA)
        bar2 = Bar(
            tala_id="triputa_chatusra",
            speed=Speed.DVITIYA,
            swaras=[
                SwaraNote("Sa", Octave.MANDRA),
                SwaraNote("Ri2"),
            ] * 8,
            saahitya=[
                SaahityaSyllable("sa"),
                SaahityaSyllable("ri"),
            ] * 8,
        )
        line1 = Line(bars=[bar1, bar1, bar1, bar1], repeat=2)
        line2 = Line(bars=[bar2, bar2], repeat=1)
        section = Section(name="pallavi", lines=[line1, line2])

        return Composition(
            title="Test Kriti",
            raga="Shankarabharanam",
            tala_id="triputa_chatusra",
            composer="Shyama Shastri",
            reference_sa_hz=261.63,
            sections=[section],
        )

    def test_round_trip_dict(self):
        comp = self._make_test_composition()
        d = composition_to_dict(comp)
        restored = composition_from_dict(d)

        assert restored.title == comp.title
        assert restored.raga == comp.raga
        assert restored.tala_id == comp.tala_id
        assert restored.composer == comp.composer
        assert restored.reference_sa_hz == comp.reference_sa_hz
        assert len(restored.sections) == len(comp.sections)

        # Check deep structure
        orig_bar = comp.sections[0].lines[0].bars[0]
        rest_bar = restored.sections[0].lines[0].bars[0]
        assert rest_bar.tala_id == orig_bar.tala_id
        assert rest_bar.speed == orig_bar.speed
        assert len(rest_bar.swaras) == len(orig_bar.swaras)
        assert rest_bar.swaras[0].swara_id == orig_bar.swaras[0].swara_id
        assert rest_bar.swaras[0].octave == orig_bar.swaras[0].octave

    def test_round_trip_file(self):
        comp = self._make_test_composition()
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False,
        ) as f:
            path = Path(f.name)

        try:
            save_composition(comp, path)
            restored = load_composition(path)

            assert restored.title == comp.title
            assert restored.composer == comp.composer
            assert len(restored.sections) == 1
            assert len(restored.sections[0].lines) == 2

            # Verify octave survives round-trip
            mandra_note = restored.sections[0].lines[1].bars[0].swaras[0]
            assert mandra_note.octave == Octave.MANDRA
        finally:
            path.unlink(missing_ok=True)

    def test_json_is_valid(self):
        comp = self._make_test_composition()
        d = composition_to_dict(comp)
        json_str = json.dumps(d, ensure_ascii=False)
        parsed = json.loads(json_str)
        assert parsed["title"] == "Test Kriti"

    def test_load_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            load_composition("/nonexistent/path.json")

    def test_speed_serialized_as_int(self):
        comp = self._make_test_composition()
        d = composition_to_dict(comp)
        bar_data = d["sections"][0]["lines"][0]["bars"][0]
        assert bar_data["speed"] == 1  # PRATAMA = 1
        bar2_data = d["sections"][0]["lines"][1]["bars"][0]
        assert bar2_data["speed"] == 2  # DVITIYA = 2

    def test_saahitya_serialized_as_strings(self):
        comp = self._make_test_composition()
        d = composition_to_dict(comp)
        bar_data = d["sections"][0]["lines"][0]["bars"][0]
        assert isinstance(bar_data["saahitya"], list)
        assert all(isinstance(s, str) for s in bar_data["saahitya"])
