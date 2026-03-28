from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.collections import CollectionName


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create indexes for alert listing and deduplication (user ↔ document join)."""

    documents = db[CollectionName.DOCUMENTS]
    await documents.create_index("source", name="idx_documents_source")

    alerts = db[CollectionName.ALERTS]

    await alerts.create_index("user_id", name="idx_alerts_user_id")
    await alerts.create_index(
        [("user_id", 1), ("is_active", 1)],
        name="idx_alerts_user_active",
    )
    await alerts.create_index(
        [("user_id", 1), ("document_id", 1)],
        unique=True,
        name="idx_alerts_user_document_unique",
    )
