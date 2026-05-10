"""GET endpoints for tala reference data and lyrics sync."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from crj_engine.tala.models import load_tala_db

router = APIRouter()

_DATA_DIR = Path(__file__).resolve().parents[4] / "data"
_LYRICS_DIR = _DATA_DIR / "lyrics"


@router.get("/talas")
async def get_talas(tradition: str | None = None) -> list[dict]:
    """Return all talas across Carnatic, Hindustani, and Dhrupad traditions.

    Optional ?tradition=carnatic|hindustani|dhrupad filter.
    """
    db = load_tala_db()
    return [
        {
            "id": t.id,
            "name": t.name,
            "base_tala": t.base_tala,
            "jati": t.jati.name.lower(),
            "jati_count": t.effective_jati_count,
            "components": t.components,
            "total_aksharas": t.total_aksharas,
            "beat_pattern": t.beat_pattern,
            "tradition": t.tradition,
            "vibhag_marks": t.vibhag_marks,
            "aliases": t.aliases,
        }
        for t in db.values()
        if tradition is None or t.tradition == tradition
    ]


@router.get("/lyrics/{track_id}")
async def get_lyrics(track_id: str) -> dict:
    """Return lyrics sync data for a track.

    Looks for ``data/lyrics/{track_id}.json``.
    """
    safe_id = track_id.replace("/", "").replace("\\", "").replace("..", "")
    path = _LYRICS_DIR / f"{safe_id}.json"

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Lyrics not found: {track_id}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    return data
