"""Composition serializer — save and load compositions as JSON."""

from __future__ import annotations

import json
from pathlib import Path

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


def _swara_to_dict(note: SwaraNote) -> dict:
    return {
        "swara_id": note.swara_id,
        "octave": note.octave.value,
    }


def _swara_from_dict(d: dict) -> SwaraNote:
    return SwaraNote(
        swara_id=d["swara_id"],
        octave=Octave(d["octave"]),
    )


def _bar_to_dict(bar: Bar) -> dict:
    return {
        "tala_id": bar.tala_id,
        "speed": bar.speed.value,
        "swaras": [_swara_to_dict(s) for s in bar.swaras],
        "saahitya": [s.text for s in bar.saahitya],
    }


def _bar_from_dict(d: dict) -> Bar:
    return Bar(
        tala_id=d["tala_id"],
        speed=Speed(d["speed"]),
        swaras=[_swara_from_dict(s) for s in d["swaras"]],
        saahitya=[SaahityaSyllable(text=t) for t in d["saahitya"]],
    )


def _line_to_dict(line: Line) -> dict:
    return {
        "bars": [_bar_to_dict(b) for b in line.bars],
        "repeat": line.repeat,
    }


def _line_from_dict(d: dict) -> Line:
    return Line(
        bars=[_bar_from_dict(b) for b in d["bars"]],
        repeat=d.get("repeat", 2),
    )


def _section_to_dict(section: Section) -> dict:
    return {
        "name": section.name,
        "lines": [_line_to_dict(ln) for ln in section.lines],
    }


def _section_from_dict(d: dict) -> Section:
    return Section(
        name=d["name"],
        lines=[_line_from_dict(ln) for ln in d["lines"]],
    )


def composition_to_dict(comp: Composition) -> dict:
    """Convert a Composition to a JSON-serializable dict."""
    return {
        "title": comp.title,
        "raga": comp.raga,
        "tala_id": comp.tala_id,
        "composer": comp.composer,
        "reference_sa_hz": comp.reference_sa_hz,
        "sections": [_section_to_dict(s) for s in comp.sections],
    }


def composition_from_dict(d: dict) -> Composition:
    """Reconstruct a Composition from a dict (parsed JSON)."""
    return Composition(
        title=d["title"],
        raga=d["raga"],
        tala_id=d["tala_id"],
        composer=d["composer"],
        reference_sa_hz=d["reference_sa_hz"],
        sections=[_section_from_dict(s) for s in d["sections"]],
    )


def save_composition(comp: Composition, path: str | Path) -> None:
    """Save a composition to a JSON file.

    Args:
        comp: The Composition to save.
        path: Output file path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = composition_to_dict(comp)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_composition(path: str | Path) -> Composition:
    """Load a composition from a JSON file.

    Args:
        path: Path to the composition JSON file.

    Returns:
        The reconstructed Composition.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Composition file not found: {path}")
    with open(path) as f:
        data = json.load(f)
    return composition_from_dict(data)
