"""Stub monitor job: upsert JSON seed documents (§4-D); replace with live scraper + scheduler."""

import logging
from datetime import UTC, datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.seed_loader import load_seed_directory

log = logging.getLogger(__name__)


async def trigger_monitor_stub(db: AsyncIOMotorDatabase) -> dict[str, object]:
    """
    Manual / scheduled entry point for `POST /v1/system:triggerMonitor`.

    Today: re-runs ``load_seed_directory`` so every ``data/seed/*.json`` upserts into MongoDB.
    Next: fetch Bloomington agendas, normalize to ``DocumentRecord`` rows, then insert/upsert.
    """
    now = datetime.now(UTC).isoformat()
    log.info("Monitor stub invoked at %s", now)
    seed_stats = await load_seed_directory(db)
    return {
        "status": "ACCEPTED",
        "message": "Monitor run accepted: seed JSON upserted (attach live scraper here).",
        "requested_at": now,
        "seed": seed_stats,
    }
