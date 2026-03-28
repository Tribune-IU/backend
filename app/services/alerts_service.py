from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.collections import CollectionName

async def generate_alert_for_user_and_doc(
    db: AsyncIOMotorDatabase, 
    user_id: str, 
    document_id: str, 
    title: str, 
    summary: str
) -> None:
    """Consolidated helper to upsert alerts across the system without duplicating template logic."""
    alert_payload = {
        "user_id": str(user_id),
        "document_id": str(document_id),
        "ai_summary": summary or f"Policy update regarding {title}.",
        "ai_draft_comment": f"As a local resident impacted by {title}, I am expressing my perspective on this proposal...",
        "is_active": True
    }
    await db[CollectionName.ALERTS].update_one(
        {"user_id": alert_payload["user_id"], "document_id": alert_payload["document_id"]},
        {"$set": alert_payload},
        upsert=True
    )
