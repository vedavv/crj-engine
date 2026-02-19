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
    """A tala from the Suladi Sapta Tala system.

    Attributes:
        id: Unique identifier (e.g. "triputa_chatusra").
        name: Display name (e.g. "Adi Tala (Chatusra)").
        base_tala: One of the 7 base talas.
        jati: The jati determining laghu count.
        components: Ordered list of tala components
            (laghu, drutam, anudrutam).
        total_aksharas: Total aksharas in one cycle.
        beat_pattern: Aksharas per component.
        aliases: Common alternative names.
    """

    id: str
    name: str
    base_tala: str
    jati: Jati
    components: list[str]
    total_aksharas: int
    beat_pattern: list[int]
    aliases: list[str] = field(default_factory=list)


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


def load_tala_db(
    path: Path | None = None,
) -> dict[str, TalaDefinition]:
    """Load the Suladi Sapta Tala database from JSON.

    Returns a dict mapping tala id to TalaDefinition.
    Results are cached after first load.
    """
    global _TALA_DB_CACHE  # noqa: PLW0603
    if _TALA_DB_CACHE is not None and path is None:
        return _TALA_DB_CACHE

    if path is None:
        path = _CONFIGS_DIR / "talas" / "carnatic_35.json"

    with open(path) as f:
        data = json.load(f)

    db: dict[str, TalaDefinition] = {}
    for entry in data["talas"]:
        jati = Jati[entry["jati"].upper()]
        tala = TalaDefinition(
            id=entry["id"],
            name=entry["name"],
            base_tala=entry["base_tala"],
            jati=jati,
            components=entry["components"],
            total_aksharas=entry["total_aksharas"],
            beat_pattern=entry["beat_pattern"],
            aliases=entry.get("aliases", []),
        )
        db[tala.id] = tala

    if path is None or path == _CONFIGS_DIR / "talas" / "carnatic_35.json":
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
