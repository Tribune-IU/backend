"""
Scraper / seed loader (§4-D): ingest structured JSON into the ``documents`` collection.

Real scrapers can write the same JSON shape (or call ``load_seed_directory`` / ``load_seed_items``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import UpdateOne

from app.db.collections import CollectionName
from app.models.document import DocumentRecord


def default_seed_dir() -> Path:
    """``backend/data/seed`` (all ``*.json`` files are loaded)."""
    backend_root = Path(__file__).resolve().parents[2]
    return backend_root / "data" / "seed"


def _read_seed_file(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Seed JSON not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        return list(raw.values())
    if not isinstance(raw, list):
        raise ValueError(f"{path.name}: Seed JSON must be a JSON array (or object map) of document objects.")
    return raw


def _rows_to_ops(rows: list[dict[str, Any]], *, filename: str) -> list[UpdateOne]:
    ops: list[UpdateOne] = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{filename}: seed item {i} must be an object.")
        
        # Inject standard fallback for required text fields if agents generated object maps instead of full documents
        raw_text = row.get("raw_text") or row.get("summary", "No raw text available.")
        
        raw_ai_tags = row.get("ai_tags", {})
        cleaned_tags = {}
        for k, v in raw_ai_tags.items():
            if isinstance(v, str):
                cleaned_tags[k] = [v]
            elif isinstance(v, list):
                cleaned_tags[k] = [str(item) for item in v]
            else:
                cleaned_tags[k] = []
        
        # Only preserve fields that the DocumentRecord strictly expects to bypass extra_forbidden
        cleaned_row = {
            "title": row.get("title", "Untitled"),
            "source": row.get("source", "unknown"),
            "raw_text": raw_text,
            "summary": row.get("summary", ""),
            "ai_tags": cleaned_tags
        }
            
        doc = DocumentRecord.model_validate(cleaned_row)
        payload = doc.model_dump(by_alias=True, exclude_none=True, exclude={"id"})
        payload.pop("_id", None)
        ops.append(UpdateOne({"source": payload["source"]}, {"$set": payload}, upsert=True))
    return ops


async def load_seed_items(
    db: AsyncIOMotorDatabase,
    path: Path | str,
) -> dict[str, int]:
    """
    Load documents from a single JSON file into MongoDB.

    Each array element must match ``DocumentRecord`` (``title``, ``source``, ``raw_text``, ``ai_tags``).
    Rows are upserted on ``source`` so the loader is safe to re-run.

    Returns: ``upserted``, ``modified``, ``total`` (rows in file), ``files`` (always ``1``).
    """
    resolved = Path(path)
    rows = _read_seed_file(resolved)
    coll = db[CollectionName.DOCUMENTS]
    ops = _rows_to_ops(rows, filename=resolved.name)

    if not ops:
        return {"upserted": 0, "modified": 0, "total": 0, "files": 1}

    result = await coll.bulk_write(ops, ordered=False)
    return {
        "upserted": result.upserted_count,
        "modified": result.modified_count,
        "total": len(ops),
        "files": 1,
    }


async def load_seed_directory(
    db: AsyncIOMotorDatabase,
    directory: Path | str | None = None,
) -> dict[str, int]:
    """
    Load every ``*.json`` file in the seed directory (sorted by path name).

    Each file must be a JSON array of ``DocumentRecord`` objects. All rows are upserted on ``source``.
    """
    root = Path(directory) if directory is not None else default_seed_dir()
    if not root.is_dir():
        raise FileNotFoundError(f"Seed directory not found: {root}")

    paths = sorted(root.glob("*.json"))
    coll = db[CollectionName.DOCUMENTS]
    all_ops: list[UpdateOne] = []
    for p in paths:
        rows = _read_seed_file(p)
        all_ops.extend(_rows_to_ops(rows, filename=p.name))

    if not all_ops:
        return {"upserted": 0, "modified": 0, "total": 0, "files": len(paths)}

    result = await coll.bulk_write(all_ops, ordered=False)
    return {
        "upserted": result.upserted_count,
        "modified": result.modified_count,
        "total": len(all_ops),
        "files": len(paths),
    }
