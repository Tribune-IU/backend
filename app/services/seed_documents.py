from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.collections import CollectionName
from app.services.seed_loader import load_seed_directory


async def ensure_seed_documents(db: AsyncIOMotorDatabase) -> dict[str, int]:
    """
    On first boot (empty ``documents``), ingest all ``*.json`` under ``data/seed`` (§4-D).

    After data exists, skips loading so ad-hoc documents are not mixed with forced re-import.
    Call ``load_seed_directory`` or ``load_seed_items`` to upsert from JSON at any time.
    """
    coll = db[CollectionName.DOCUMENTS]
    if await coll.find_one():
        return {"upserted": 0, "modified": 0, "total": 0, "files": 0, "skipped": 1}
    out = await load_seed_directory(db)
    return {**out, "skipped": 0}
