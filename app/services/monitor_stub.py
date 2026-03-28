"""Stub monitor job: upsert JSON seed documents (§4-D); replace with live scraper + scheduler."""

import logging
from datetime import UTC, datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.services.seed_loader import load_seed_directory

log = logging.getLogger(__name__)


async def trigger_monitor_stub(db: AsyncIOMotorDatabase) -> dict[str, object]:
    """
    Simulates scraping by loading the pre-parsed JSON seed files directly into the database.
    Because the seed files are assumed to already contain the LLM outputs, we bypass the agent
    here and immediately hook into the coalition matcher to generate alerts.
    """
    now = datetime.now(UTC).isoformat()
    log.info("Monitor stub invoked at %s (bypassing agent due to pre-parsed seeds)", now)
    
    from app.services.seed_loader import load_seed_directory
    from app.services.coalition_matcher import find_users_for_document
    from app.db.collections import CollectionName
    
    # 1. Load the fully parsed seed objects into the DB natively
    seed_stats = await load_seed_directory(db)
    
    # 2. Simulate the webhook alert generation for every document in the DB just in case
    # In a real deployed app, the scraper pushes individual documents to `POST /v1/system:saveDocument`.
    from app.services.alerts_service import generate_alert_for_user_and_doc
    cursor = db[CollectionName.DOCUMENTS].find({})
    total_alerts_inserted = 0
    
    async for doc in cursor:
        matched_users = await find_users_for_document(db, document=doc)
        if matched_users:
            for u in matched_users:
                title = doc.get("title", "Untitled")
                await generate_alert_for_user_and_doc(
                    db=db,
                    user_id=str(u["_id"]),
                    document_id=str(doc["_id"]),
                    title=title,
                    summary=doc.get("summary", "")
                )
                total_alerts_inserted += 1
                
    return {
        "status": "ACCEPTED",
        "message": f"Pre-parsed seeds ingested cleanly. Generated {total_alerts_inserted} alerts.",
        "requested_at": now,
        "seed": seed_stats,
    }
