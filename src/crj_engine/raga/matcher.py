"""Rule-based raga identification — match swara sequences against Melakarta database."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_CONFIGS_DIR = Path(__file__).resolve().parents[3] / "configs"

# Canonical swara ordering (chromatic position, 0-11)
SWARA_POSITION = {
    "Sa": 0, "Ri1": 1, "Ri2": 2, "Ga1": 2, "Ga2": 3, "Ri3": 3,
    "Ga3": 4, "Ma1": 5, "Ma2": 6, "Pa": 7, "Dha1": 8, "Dha2": 9,
    "Ni1": 9, "Ni2": 10, "Dha3": 10, "Ni3": 11,
}

# Enharmonic pairs: position -> list of valid swara names at that position
ENHARMONIC_MAP = {
    0: ["Sa"], 1: ["Ri1"], 2: ["Ri2", "Ga1"], 3: ["Ga2", "Ri3"],
    4: ["Ga3"], 5: ["Ma1"], 6: ["Ma2"], 7: ["Pa"],
    8: ["Dha1"], 9: ["Dha2", "Ni1"], 10: ["Ni2", "Dha3"], 11: ["Ni3"],
}


@dataclass
class RagaDefinition:
    """A raga from the Melakarta database."""

    number: int
    name: str
    arohana: list[str]
    avarohana: list[str]
    ma_type: str
    ri_ga: list[str]
    dha_ni: list[str]
    aliases: list[str] = field(default_factory=list)

    @property
    def swara_set(self) -> set[int]:
        """Return the set of chromatic positions used by this raga."""
        positions = set()
        for swara in self.arohana:
            if swara in SWARA_POSITION:
                positions.add(SWARA_POSITION[swara])
        return positions

    @property
    def swara_names(self) -> set[str]:
        """Return the set of swara names (without Sa at end) used by this raga."""
        names = set()
        for swara in self.arohana:
            if swara != "Sa" or len(names) == 0:
                names.add(swara)
        return names


@dataclass
class RagaCandidate:
    """A candidate raga match with confidence score."""

    raga: RagaDefinition
    confidence: float
    match_details: dict = field(default_factory=dict)


class RagaMatcher:
    """Rule-based raga identification using arohana/avarohana matching."""

    def __init__(self, db_path: str | Path | None = None):
        self.ragas: list[RagaDefinition] = []
        path = Path(db_path) if db_path else _CONFIGS_DIR / "ragas" / "melakarta_72.json"
        self._load_database(path)

    def _load_database(self, path: Path) -> None:
        """Load the Melakarta raga database from JSON."""
        with open(path) as f:
            data = json.load(f)

        for entry in data["ragas"]:
            self.ragas.append(RagaDefinition(
                number=entry["number"],
                name=entry["name"],
                arohana=entry["arohana"],
                avarohana=entry["avarohana"],
                ma_type=entry["ma_type"],
                ri_ga=entry["ri_ga"],
                dha_ni=entry["dha_ni"],
                aliases=entry.get("aliases", []),
            ))

    def _normalize_swara(self, swara: str) -> int:
        """Convert a swara name to its chromatic position (0-11)."""
        # Handle upper octave Sa
        if swara == "Sa" or swara == "Sa'":
            return 0
        if swara in SWARA_POSITION:
            return SWARA_POSITION[swara]
        raise ValueError(f"Unknown swara: {swara}")

    def _swara_set_from_names(self, swaras: list[str]) -> set[int]:
        """Convert a list of swara names to a set of chromatic positions."""
        return {self._normalize_swara(s) for s in swaras}

    def _compute_set_match(
        self, detected_positions: set[int], raga: RagaDefinition
    ) -> float:
        """Compute how well the detected swara set matches a raga.

        Returns a score between 0.0 and 1.0.
        """
        raga_positions = raga.swara_set

        # Intersection: swaras present in both detected and raga
        common = detected_positions & raga_positions
        # Swaras in detected but not in raga (foreign notes)
        foreign = detected_positions - raga_positions
        # Swaras in raga but not detected (missing notes — less penalized)
        missing = raga_positions - detected_positions

        if len(raga_positions) == 0:
            return 0.0

        # Coverage: what fraction of the raga's swaras did we detect?
        coverage = len(common) / len(raga_positions)

        # Purity: what fraction of detected swaras belong to the raga?
        purity = len(common) / len(detected_positions) if detected_positions else 0.0

        # Foreign note penalty: stronger than missing note penalty
        foreign_penalty = len(foreign) * 0.15
        missing_penalty = len(missing) * 0.05

        score = (0.6 * coverage + 0.4 * purity) - foreign_penalty - missing_penalty
        return max(0.0, min(1.0, score))

    def _compute_sequence_match(
        self, detected_swaras: list[str], raga: RagaDefinition
    ) -> float:
        """Compute how well the detected swara sequence matches raga phrases.

        Looks for arohana/avarohana subsequence patterns.
        Returns a bonus score between 0.0 and 0.3.
        """
        if len(detected_swaras) < 3:
            return 0.0

        detected_positions = [self._normalize_swara(s) for s in detected_swaras]
        arohana_positions = [self._normalize_swara(s) for s in raga.arohana]
        avarohana_positions = [self._normalize_swara(s) for s in raga.avarohana]

        # Check for ascending runs matching arohana
        ascending_matches = 0
        for i in range(len(detected_positions) - 2):
            window = detected_positions[i : i + 3]
            if window[0] < window[1] < window[2]:
                # Check if this ascending triple exists in arohana
                for j in range(len(arohana_positions) - 2):
                    if arohana_positions[j : j + 3] == window:
                        ascending_matches += 1
                        break

        # Check for descending runs matching avarohana
        descending_matches = 0
        for i in range(len(detected_positions) - 2):
            window = detected_positions[i : i + 3]
            if window[0] > window[1] > window[2]:
                for j in range(len(avarohana_positions) - 2):
                    if avarohana_positions[j : j + 3] == window:
                        descending_matches += 1
                        break

        total_windows = max(1, len(detected_positions) - 2)
        sequence_score = (ascending_matches + descending_matches) / total_windows
        return min(0.3, sequence_score * 0.3)

    def identify(
        self,
        detected_swaras: list[str],
        top_n: int = 5,
    ) -> list[RagaCandidate]:
        """Identify the most likely ragas given a sequence of detected swaras.

        Args:
            detected_swaras: Ordered list of swara names detected from audio
                             (e.g. ["Sa", "Ri2", "Ga3", "Ma1", "Pa", ...]).
            top_n: Number of top candidates to return.

        Returns:
            List of RagaCandidate sorted by confidence (highest first).
        """
        if not detected_swaras:
            return []

        detected_positions = self._swara_set_from_names(detected_swaras)
        candidates = []

        for raga in self.ragas:
            set_score = self._compute_set_match(detected_positions, raga)
            seq_bonus = self._compute_sequence_match(detected_swaras, raga)
            total = min(1.0, set_score + seq_bonus)

            if total > 0.1:  # filter out very low matches
                candidates.append(RagaCandidate(
                    raga=raga,
                    confidence=round(total, 3),
                    match_details={
                        "set_score": round(set_score, 3),
                        "sequence_bonus": round(seq_bonus, 3),
                        "detected_positions": sorted(detected_positions),
                        "raga_positions": sorted(raga.swara_set),
                    },
                ))

        candidates.sort(key=lambda c: c.confidence, reverse=True)
        return candidates[:top_n]

    def resolve_enharmonic(
        self,
        position: int,
        raga: RagaDefinition,
    ) -> str:
        """Resolve an enharmonic ambiguity using raga context.

        Given a chromatic position that could be two swara names
        (e.g., position 2 = Ri2 or Ga1), return the correct name
        for the given raga.
        """
        possible_names = ENHARMONIC_MAP.get(position, [])

        if len(possible_names) <= 1:
            return possible_names[0] if possible_names else f"pos_{position}"

        # Check which name appears in the raga's arohana
        raga_swaras = set(raga.arohana + raga.avarohana)
        for name in possible_names:
            if name in raga_swaras:
                return name

        # Default to first option
        return possible_names[0]

    def get_raga_by_number(self, number: int) -> RagaDefinition | None:
        """Look up a Melakarta raga by its number (1-72)."""
        for raga in self.ragas:
            if raga.number == number:
                return raga
        return None

    def get_raga_by_name(self, name: str) -> RagaDefinition | None:
        """Look up a raga by name or alias (case-insensitive)."""
        name_lower = name.lower()
        for raga in self.ragas:
            if raga.name.lower() == name_lower:
                return raga
            if any(a.lower() == name_lower for a in raga.aliases):
                return raga
        return None
