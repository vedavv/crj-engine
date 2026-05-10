"""Tala composition data model — structures for Carnatic music notation.

Provides dataclasses for composing music with:
- Tala (rhythmic cycle) definitions
- Swara notes with octave marking (mandra/madhya/tara)
- Saahitya (lyrics) syllable alignment
- Bar, Line, Section, and Composition hierarchy
- Speed variations (pratama/dvitiya/tritiya kala)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

_CONFIGS_DIR = Path(__file__).resolve().parents[3] / "configs"


class Octave(Enum):
    """Sthayi (octave register) for swara notation."""

    MANDRA = "mandra"    # lower octave — dot below
    MADHYA = "madhya"    # middle octave — no mark
    TARA = "tara"        # upper octave — dot above


class Speed(Enum):
    """Kala (speed) — determines how many swaras fit per akshara."""

    PRATAMA = 1   # normal speed: 1 swara per akshara
    DVITIYA = 2   # double speed: 2 swaras per akshara
    TRITIYA = 3   # triple speed: 3 swaras per akshara


class Jati(Enum):
    """Jati — determines the laghu count in a tala."""

    TISRA = 3
    CHATUSRA = 4
    KHANDA = 5
    MISRA = 7
    SANKEERNA = 9


@dataclass
class TalaDefinition:
    """A tala definition spanning Carnatic, Hindustani, and Dhrupad traditions.

    Attributes:
        id: Unique identifier (e.g. "triputa_chatusra", "teentaal").
        name: Display name.
        base_tala: For Carnatic: one of the 7 base talas. For Hindustani/
            Dhrupad: the tala's own name (Teentaal, Chautal, etc.).
        jati: The jati determining laghu count (Carnatic) or matras-per-vibhag
            for Hindustani approximation.
        components: Ordered list of tala components — for Carnatic these are
            (laghu, drutam, anudrutam); for Hindustani/Dhrupad they are vibhags.
        total_aksharas: Total beats in one cycle.
        beat_pattern: Aksharas/matras per component.
        tradition: "carnatic" | "hindustani" | "dhrupad". Determines how the
            tala displays and which percussion instrument is the conventional
            default.
        vibhag_marks: For Hindustani/Dhrupad — sam/tali/khali per vibhag,
            aligned 1:1 with beat_pattern. None for Carnatic.
        aliases: Common alternative names.
    """

    id: str
    name: str
    base_tala: str
    jati: Jati
    components: list[str]
    total_aksharas: int
    beat_pattern: list[int]
    tradition: str = "carnatic"
    vibhag_marks: list[str] | None = None
    aliases: list[str] = field(default_factory=list)
    # For Hindustani/Dhrupad where the Jati enum doesn't apply naturally
    # (e.g. Ektaal vibhags are 2 matras each, not 4), the JSON file may
    # supply an explicit jati_count. Falls back to jati.value when None.
    jati_count_override: int | None = None

    @property
    def effective_jati_count(self) -> int:
        return self.jati_count_override or self.jati.value


@dataclass
class SwaraNote:
    """A single swara in a composition bar.

    Attributes:
        swara_id: Swara identifier (e.g. "Sa", "Ri2", "Ga3", "Pa").
            Use "-" for a rest and "," for a sustain of the previous note.
        octave: The octave register (mandra/madhya/tara).
    """

    swara_id: str
    octave: Octave = Octave.MADHYA


@dataclass
class SaahityaSyllable:
    """A single lyric syllable aligned to a swara position.

    Attributes:
        text: The syllable text (e.g. "sa", "ra", "nam").
            Use "-" for a sustain and "" for empty/instrumental.
    """

    text: str


@dataclass
class Bar:
    """A single bar (one tala cycle) within a composition line.

    The number of swara/saahitya positions in a bar equals
    ``total_aksharas * speed.value``. For Adi tala at dvitiya kala:
    8 * 2 = 16 positions.

    Attributes:
        tala_id: Reference to the tala definition being used.
        speed: Kala (1x, 2x, 3x).
        swaras: Swara notes for this bar.
        saahitya: Lyrics syllables aligned 1:1 with swaras.
    """

    tala_id: str
    speed: Speed
    swaras: list[SwaraNote]
    saahitya: list[SaahityaSyllable]

    @property
    def num_positions(self) -> int:
        """Number of swara/saahitya positions in this bar."""
        return len(self.swaras)

    def validate(self, tala_db: dict[str, TalaDefinition] | None = None) -> None:
        """Check that swaras and saahitya are aligned and sizes are correct.

        Raises:
            ValueError: If the bar is malformed.
        """
        if len(self.swaras) != len(self.saahitya):
            raise ValueError(
                f"Swara count ({len(self.swaras)}) != saahitya count "
                f"({len(self.saahitya)}). Must be 1:1 aligned."
            )
        if tala_db and self.tala_id in tala_db:
            expected = tala_db[self.tala_id].total_aksharas * self.speed.value
            if len(self.swaras) != expected:
                raise ValueError(
                    f"Bar has {len(self.swaras)} positions but "
                    f"{self.tala_id} at {self.speed.name} kala "
                    f"expects {expected}."
                )


@dataclass
class Line:
    """A line of composition — typically 4 bars, repeated twice.

    Attributes:
        bars: The bars in this line.
        repeat: How many times this line is performed (default 2).
    """

    bars: list[Bar]
    repeat: int = 2


@dataclass
class Section:
    """A section of a composition (pallavi, anupallavi, charanam).

    Attributes:
        name: Section name.
        lines: The lines in this section.
    """

    name: str
    lines: list[Line]


@dataclass
class Composition:
    """A complete Carnatic music composition.

    Attributes:
        title: Composition title.
        raga: Raga name (e.g. "Shankarabharanam").
        tala_id: Primary tala used.
        composer: Composer name.
        reference_sa_hz: The Sa frequency for this composition.
        sections: Ordered list of sections (pallavi, anupallavi, etc.).
    """

    title: str
    raga: str
    tala_id: str
    composer: str
    reference_sa_hz: float
    sections: list[Section]


# ---------------------------------------------------------------------------
# Tala database loading
# ---------------------------------------------------------------------------

_TALA_DB_CACHE: dict[str, TalaDefinition] | None = None


def _talas_from_file(path: Path) -> list[TalaDefinition]:
    """Load tala definitions from a single JSON file.

    The file may declare a top-level "tradition" string that all talas inherit;
    individual tala entries can override via their own "tradition" field.

    Files without a top-level "talas" key are silently skipped — keeps
    sibling config files (e.g. stroke_patterns.json) co-located in the
    talas/ directory without confusing the loader.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if "talas" not in data:
        return []

    file_tradition = data.get("tradition", "carnatic")
    out: list[TalaDefinition] = []
    for entry in data["talas"]:
        # Default jati for non-Carnatic talas where the concept doesn't apply
        # cleanly: we still need *something* in the field so existing callers
        # don't break. Chatusra (4) is the safest default.
        jati_str = entry.get("jati", "chatusra")
        jati = Jati[jati_str.upper()]
        # Honour an explicit jati_count from JSON only when it differs from
        # the enum (i.e. only when the tala's vibhag count diverges from the
        # jati enum's value — typical for Hindustani vibhag-based talas).
        json_jati_count = entry.get("jati_count")
        override = (
            json_jati_count
            if json_jati_count is not None and json_jati_count != jati.value
            else None
        )
        out.append(
            TalaDefinition(
                id=entry["id"],
                name=entry["name"],
                base_tala=entry["base_tala"],
                jati=jati,
                components=entry["components"],
                total_aksharas=entry["total_aksharas"],
                beat_pattern=entry["beat_pattern"],
                tradition=entry.get("tradition", file_tradition),
                vibhag_marks=entry.get("vibhag_marks"),
                aliases=entry.get("aliases", []),
                jati_count_override=override,
            )
        )
    return out


def load_tala_db(
    path: Path | None = None,
) -> dict[str, TalaDefinition]:
    """Load all tala databases under configs/talas/ and merge them.

    When called with no `path`, every `*.json` file in `configs/talas/` is
    loaded and merged. The result is cached after the first call.
    Pass an explicit `path` to load a single file (no caching).
    """
    global _TALA_DB_CACHE  # noqa: PLW0603

    if path is not None:
        db: dict[str, TalaDefinition] = {}
        for tala in _talas_from_file(path):
            db[tala.id] = tala
        return db

    if _TALA_DB_CACHE is not None:
        return _TALA_DB_CACHE

    talas_dir = _CONFIGS_DIR / "talas"
    db = {}
    for json_path in sorted(talas_dir.glob("*.json")):
        for tala in _talas_from_file(json_path):
            if tala.id in db:
                # Skip duplicate ids — first file wins. carnatic_35.json comes
                # alphabetically before hindustani.json/dhrupad.json so it's
                # naturally given precedence on collisions.
                continue
            db[tala.id] = tala

    _TALA_DB_CACHE = db
    return db


def get_tala(tala_id: str) -> TalaDefinition:
    """Look up a tala by id or alias.

    Raises:
        KeyError: If no matching tala is found.
    """
    db = load_tala_db()

    # Direct lookup
    if tala_id in db:
        return db[tala_id]

    # Search by alias (case-insensitive)
    tala_lower = tala_id.lower()
    for tala in db.values():
        if tala.name.lower() == tala_lower:
            return tala
        if any(a.lower() == tala_lower for a in tala.aliases):
            return tala

    raise KeyError(f"Tala not found: {tala_id}")
