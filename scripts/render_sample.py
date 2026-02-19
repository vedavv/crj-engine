#!/usr/bin/env python3
"""Render a sample Shankarabharanam composition in Adi tala to WAV files.

Generates 3 versions (sine, voice, string) plus a standalone tanpura drone.
Output: data/peer-test/audio/rendered_*.wav
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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
from crj_engine.synthesis.render import (
    ToneType,
    generate_tanpura,
    render_composition,
    save_wav,
)

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "peer-test" / "audio"
REFERENCE_SA_HZ = 261.63  # C4


def _note(swara_id: str, octave: Octave = Octave.MADHYA) -> SwaraNote:
    return SwaraNote(swara_id=swara_id, octave=octave)


def _syl(text: str) -> SaahityaSyllable:
    return SaahityaSyllable(text=text)


def build_shankarabharanam_composition() -> Composition:
    """Build a simple Shankarabharanam scale composition in Adi tala."""

    # Bar 1: Ascending scale (Sa Ri Ga Ma Pa Dha Ni Sa)
    bar1 = Bar(
        tala_id="triputa_chatusra",
        speed=Speed.PRATAMA,
        swaras=[
            _note("Sa"), _note("Ri2"), _note("Ga3"), _note("Ma1"),
            _note("Pa"), _note("Dha2"), _note("Ni3"),
            _note("Sa", Octave.TARA),
        ],
        saahitya=[
            _syl("sa"), _syl("ri"), _syl("ga"), _syl("ma"),
            _syl("pa"), _syl("dha"), _syl("ni"), _syl("sa"),
        ],
    )

    # Bar 2: Descending scale (Sa Ni Dha Pa Ma Ga Ri Sa)
    bar2 = Bar(
        tala_id="triputa_chatusra",
        speed=Speed.PRATAMA,
        swaras=[
            _note("Sa", Octave.TARA), _note("Ni3"), _note("Dha2"),
            _note("Pa"), _note("Ma1"), _note("Ga3"), _note("Ri2"),
            _note("Sa"),
        ],
        saahitya=[
            _syl("sa"), _syl("ni"), _syl("dha"), _syl("pa"),
            _syl("ma"), _syl("ga"), _syl("ri"), _syl("sa"),
        ],
    )

    # Bar 3: A simple phrase (Sa Ga Pa , Dha Pa Ga Ri)
    bar3 = Bar(
        tala_id="triputa_chatusra",
        speed=Speed.PRATAMA,
        swaras=[
            _note("Sa"), _note("Ga3"), _note("Pa"), _note(","),
            _note("Dha2"), _note("Pa"), _note("Ga3"), _note("Ri2"),
        ],
        saahitya=[
            _syl("sa"), _syl("ri"), _syl("ga"), _syl("-"),
            _syl("ma"), _syl("pa"), _syl("dha"), _syl("ni"),
        ],
    )

    # Bar 4: Return to Sa (Sa , , , Sa , , ,)
    bar4 = Bar(
        tala_id="triputa_chatusra",
        speed=Speed.PRATAMA,
        swaras=[
            _note("Sa"), _note(","), _note(","), _note(","),
            _note("Sa"), _note(","), _note(","), _note(","),
        ],
        saahitya=[
            _syl("sa"), _syl("-"), _syl("-"), _syl("-"),
            _syl("sa"), _syl("-"), _syl("-"), _syl("-"),
        ],
    )

    # Build composition: 2 lines, each repeated twice
    line1 = Line(bars=[bar1, bar2], repeat=2)
    line2 = Line(bars=[bar3, bar4], repeat=2)

    pallavi = Section(name="pallavi", lines=[line1, line2])

    return Composition(
        title="Shankarabharanam Scale Exercise",
        raga="Shankarabharanam",
        tala_id="triputa_chatusra",
        composer="CRJ Studio",
        reference_sa_hz=REFERENCE_SA_HZ,
        sections=[pallavi],
    )


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    comp = build_shankarabharanam_composition()
    tempo = 80  # BPM

    print(f"Composition: {comp.title}")
    print(f"Raga: {comp.raga} | Tala: {comp.tala_id} | Tempo: {tempo} BPM")
    print(f"Sa = {REFERENCE_SA_HZ} Hz\n")

    # Render in each tone type
    for tone_type in ToneType:
        print(f"Rendering {tone_type.value} tone...")
        audio = render_composition(
            comp, tempo_bpm=tempo, tone=tone_type,
            include_tanpura=True,
        )
        filename = f"rendered_{tone_type.value}.wav"
        path = OUTPUT_DIR / filename
        save_wav(audio, path)
        duration = len(audio) / 44100
        print(f"  Saved: {path} ({duration:.1f}s)")

    # Also render standalone tanpura drone
    print("\nRendering tanpura drone (10s)...")
    tanpura = generate_tanpura(REFERENCE_SA_HZ, duration_s=10.0)
    tanpura_path = OUTPUT_DIR / "tanpura_drone.wav"
    save_wav(tanpura, tanpura_path)
    print(f"  Saved: {tanpura_path}")

    print("\nDone! Open the WAV files in any audio player to listen.")


if __name__ == "__main__":
    main()
