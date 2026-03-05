"""CRUD API for compositions."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException

from crj_engine.api.schemas import CompositionIn, CompositionOut
from crj_engine.tala.serializer import composition_from_dict, composition_to_dict

router = APIRouter()

_DATA_DIR = Path(__file__).resolve().parents[4] / "data" / "compositions"


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _index_path() -> Path:
    return _DATA_DIR / "_index.json"


def _load_index() -> dict[str, dict]:
    """Load the composition index (id -> metadata)."""
    path = _index_path()
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save_index(index: dict[str, dict]) -> None:
    _ensure_dir()
    with open(_index_path(), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


@router.post("/compositions", response_model=CompositionOut)
async def create_composition(body: CompositionIn) -> CompositionOut:
    """Save a new composition."""
    _ensure_dir()
    comp_id = str(uuid.uuid4())[:8]

    comp_data = body.model_dump()
    comp_data["id"] = comp_id

    # Save the full composition file
    path = _DATA_DIR / f"{comp_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(comp_data, f, indent=2, ensure_ascii=False)

    # Update index
    index = _load_index()
    index[comp_id] = {
        "id": comp_id,
        "title": comp_data.get("title", "Untitled"),
        "raga": comp_data.get("raga", ""),
        "tala_id": comp_data.get("tala_id", ""),
        "composer": comp_data.get("composer", ""),
    }
    _save_index(index)

    return CompositionOut(id=comp_id, **body.model_dump())


@router.get("/compositions", response_model=list[dict])
async def list_compositions() -> list[dict]:
    """List all saved compositions (metadata only)."""
    index = _load_index()
    return list(index.values())


@router.get("/compositions/{comp_id}", response_model=CompositionOut)
async def get_composition(comp_id: str) -> CompositionOut:
    """Get one composition by ID."""
    safe_id = comp_id.replace("/", "").replace("\\", "").replace("..", "")
    path = _DATA_DIR / f"{safe_id}.json"

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Composition not found: {comp_id}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    return CompositionOut(**data)


@router.put("/compositions/{comp_id}", response_model=CompositionOut)
async def update_composition(comp_id: str, body: CompositionIn) -> CompositionOut:
    """Update an existing composition."""
    safe_id = comp_id.replace("/", "").replace("\\", "").replace("..", "")
    path = _DATA_DIR / f"{safe_id}.json"

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Composition not found: {comp_id}")

    comp_data = body.model_dump()
    comp_data["id"] = safe_id

    with open(path, "w", encoding="utf-8") as f:
        json.dump(comp_data, f, indent=2, ensure_ascii=False)

    # Update index
    index = _load_index()
    index[safe_id] = {
        "id": safe_id,
        "title": comp_data.get("title", "Untitled"),
        "raga": comp_data.get("raga", ""),
        "tala_id": comp_data.get("tala_id", ""),
        "composer": comp_data.get("composer", ""),
    }
    _save_index(index)

    return CompositionOut(id=safe_id, **body.model_dump())


@router.delete("/compositions/{comp_id}")
async def delete_composition(comp_id: str) -> dict:
    """Delete a composition."""
    safe_id = comp_id.replace("/", "").replace("\\", "").replace("..", "")
    path = _DATA_DIR / f"{safe_id}.json"

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Composition not found: {comp_id}")

    path.unlink()

    # Update index
    index = _load_index()
    index.pop(safe_id, None)
    _save_index(index)

    return {"status": "deleted", "id": safe_id}
