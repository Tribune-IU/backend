import logging

from fastapi import APIRouter
from pydantic import BaseModel
from app.db.collections import CollectionName

logger = logging.getLogger(__name__)
from app.api.validation import parse_object_id
from app.models.document import DocumentRecord

from app.api.deps import DbDep
from app.schemas.v1 import TriggerMonitorResponse
from app.schemas.v1_system import SaveProfileBody, SaveDocumentBody
from app.services.monitor_stub import trigger_monitor_stub
from app.services.reply_store import qa_reply_store, draft_comment_store

router = APIRouter(tags=["system"])


@router.post("/system:triggerMonitor", response_model=TriggerMonitorResponse)
async def trigger_monitor(db: DbDep) -> TriggerMonitorResponse:
    data = await trigger_monitor_stub(db)
    return TriggerMonitorResponse.model_validate(data)


@router.post("/system:saveProfile")
async def save_profile(body: SaveProfileBody, db: DbDep) -> dict:
    logger.info("SYSTEM saveProfile  user_id=%s", body.user_id)
    oid = parse_object_id(body.user_id, field="user_id")
    updated_profile = body.profile_data.model_dump()
    await db[CollectionName.USERS].update_one(
        {"_id": oid},
        {"$set": {"parsed_profile": updated_profile}}
    )
    
    # After a user profile is tagged, immediately check all existing documents to generate alerts!
    from app.services.tag_utils import flatten_tag_dict, check_tags_overlap
    from app.services.alerts_service import generate_alert_for_user_and_doc
    user_tag_list = flatten_tag_dict(updated_profile)
    
    cursor = db[CollectionName.DOCUMENTS].find({})
    
    async for doc in cursor:
        doc_tags = doc.get("ai_tags", {})
        doc_tag_list = flatten_tag_dict(doc_tags)
        
        # If the user's tags intersect with the document's tags:
        if check_tags_overlap(user_tag_list, doc_tag_list):
            title = doc.get("title", "Unknown Proposal")
            logger.info("SYSTEM saveProfile  alert generated  user_id=%s  doc_id=%s  title=%r", str(oid), str(doc["_id"]), title[:60])
            await generate_alert_for_user_and_doc(
                db=db,
                user_id=str(oid),
                document_id=str(doc["_id"]),
                title=title,
                summary=doc.get("summary", "")
            )

    return {"status": "success"}


@router.post("/system:saveDocument")
async def save_document(body: SaveDocumentBody, db: DbDep) -> dict:
    agent_data = body.data
    source = agent_data.source or "unknown"
    title = agent_data.title or "Untitled"
    
    # Extract tags from the strongly typed Pydantic body
    ai_tags = {
        "topics": agent_data.ai_tags.topics,
        "impact_radius": [agent_data.ai_tags.impact_radius] if agent_data.ai_tags.impact_radius else [],
        "affected_groups": agent_data.ai_tags.affected_groups,
    }

    payload = {
        "title": title,
        "source": source,
        "ai_tags": ai_tags
    }
    doc_res = await db[CollectionName.DOCUMENTS].update_one(
        {"source": source},
        {"$set": payload},
        upsert=True
    )
    
    doc_id = doc_res.upserted_id
    if not doc_id:
        existing = await db[CollectionName.DOCUMENTS].find_one({"source": source})
        if existing:
            doc_id = existing["_id"]
            
    if doc_id:
        from app.services.coalition_matcher import find_users_for_document
        from app.services.alerts_service import generate_alert_for_user_and_doc
        matched_users = await find_users_for_document(db, document=payload)
        
        if matched_users:
            for u in matched_users:
                await generate_alert_for_user_and_doc(
                    db=db,
                    user_id=str(u["_id"]),
                    document_id=str(doc_id),
                    title=title,
                    summary=agent_data.summary
                )
            
    return {"status": "success"}


# ---------------------------------------------------------------------------
# Agent webhook receivers
# These are called BY the ADK agents, not by end-users.
# ---------------------------------------------------------------------------

class SaveQaReplyBody(BaseModel):
    session_id: str
    reply: str


class SaveDraftCommentBody(BaseModel):
    session_id: str
    draft_comment: str


@router.post("/system:saveQaReply")
async def save_qa_reply(body: SaveQaReplyBody) -> dict:
    """Receive an answer from document_qa_agent and unblock the waiting chat handler."""
    logger.info("SYSTEM saveQaReply  session=%s  reply_len=%d  preview=%r", body.session_id, len(body.reply), body.reply[:80])
    await qa_reply_store.set(body.session_id, body.reply)
    return {"status": "ok"}


@router.post("/system:saveDraftComment")
async def save_draft_comment(body: SaveDraftCommentBody) -> dict:
    """Receive a draft letter from draft_comment_agent and unblock the waiting draft handler."""
    logger.info("SYSTEM saveDraftComment  session=%s  draft_len=%d  preview=%r", body.session_id, len(body.draft_comment), body.draft_comment[:80])
    await draft_comment_store.set(body.session_id, body.draft_comment)
    return {"status": "ok"}

