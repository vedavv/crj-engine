"""Octave notation rendering — Unicode combining marks for swara display.

Carnatic notation convention:
  - Mandra sthayi (lower octave): dot below the swara letter
  - Madhya sthayi (middle octave): no mark
  - Tara sthayi (upper octave): dot above the swara letter

This module uses Unicode combining characters:
  - U+0323 (combining dot below) for mandra
  - U+0307 (combining dot above) for tara
"""

from __future__ import annotations

import json
from pathlib import Path

from crj_engine.tala.models import Bar, Octave, SwaraNote

_CONFIGS_DIR = Path(__file__).resolve().parents[3] / "configs"

# Unicode combining marks
_DOT_BELOW = "\u0323"  # combining dot below (mandra)
_DOT_ABOVE = "\u0307"  # combining dot above (tara)

# Cache for swara name lookups
_SWARA_NAMES_CACHE: dict[str, dict[str, str]] | None = None


def _load_swara_names() -> dict[str, dict[str, str]]:
    """Load swara display names from swarasthanas.json.

    Returns a dict mapping swara_id -> {script -> short_name}.
    """
    global _SWARA_NAMES_CACHE  # noqa: PLW0603
    if _SWARA_NAMES_CACHE is not None:
        return _SWARA_NAMES_CACHE

    config_path = _CONFIGS_DIR / "swarasthanas.json"
    with open(config_path) as f:
        data = json.load(f)

    names: dict[str, dict[str, str]] = {}
    for swara in data["swarasthanas"]:
        names[swara["id"]] = swara["names"]

    _SWARA_NAMES_CACHE = names
    return names


def _apply_octave_mark(text: str, octave: Octave) -> str:
    """Apply the appropriate Unicode combining mark to text.

    The combining mark is inserted after the first character so it
    appears as a dot above or below that character.
    """
    if not text or text == "-" or text == ",":
        return text

    if octave == Octave.MANDRA:
        return text[0] + _DOT_BELOW + text[1:]
    elif octave == Octave.TARA:
        return text[0] + _DOT_ABOVE + text[1:]
    else:
        return text


def render_swara(
    note: SwaraNote,
    script: str = "iast",
) -> str:
    """Render a single swara note with octave marking.

    Args:
        note: The SwaraNote to render.
        script: Which script to use for display
            ("iast", "devanagari", "kannada", "tamil", "telugu").

    Returns:
        The swara name with appropriate octave mark applied.
        Returns "-" for rests and "," for sustains.
    """
    # Special symbols pass through
    if note.swara_id in ("-", ","):
        return note.swara_id

    swara_names = _load_swara_names()
    if note.swara_id in swara_names:
        display = swara_names[note.swara_id].get(script, note.swara_id)
    else:
        display = note.swara_id

    return _apply_octave_mark(display, note.octave)


def render_bar_swaras(
    bar: Bar,
    script: str = "iast",
    separator: str = " ",
) -> str:
    """Render the swara row of a bar.

    Args:
        bar: The bar to render.
        script: Script for swara names.
        separator: Separator between swara positions.

    Returns:
        A string like "Sa Ri2 Ga3 Ma1 | Pa Dha2 Ni3 Sa"
    """
    parts = [render_swara(n, script) for n in bar.swaras]
    return separator.join(parts)


def render_bar_saahitya(
    bar: Bar,
    separator: str = " ",
) -> str:
    """Render the saahitya (lyrics) row of a bar.

    Args:
        bar: The bar to render.
        separator: Separator between syllable positions.

    Returns:
        A string like "sa ri ga ma | pa dha ni sa"
    """
    parts = [s.text for s in bar.saahitya]
    return separator.join(parts)


def render_bar(
    bar: Bar,
    script: str = "iast",
    separator: str = " ",
) -> str:
    """Render a complete bar with aligned swara and saahitya rows.

    Returns a two-line string:
        Line 1: Swara notes with octave marks
        Line 2: Saahitya syllables
    """
    swara_line = render_bar_swaras(bar, script, separator)
    saahitya_line = render_bar_saahitya(bar, separator)
    return f"{swara_line}\n{saahitya_line}"
