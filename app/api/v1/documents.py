import logging
import uuid

from fastapi import APIRouter

logger = logging.getLogger(__name__)

from app.api.deps import DbDep
from app.api.errors import ApiError
from app.api.validation import parse_object_id
from app.config import settings
from app.db.collections import CollectionName
from app.db.mongo_utils import mongo_doc_to_response
from app.schemas.v1 import (
    ChatBody,
    ChatResponse,
    DocumentDetail,
    DocumentListItem,
    DraftCommentBody,
    DraftCommentResponse,
    ListDocumentsResponse,
)
from app.services.agents import trigger_document_qa_agent, trigger_draft_comment_agent

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=ListDocumentsResponse)
async def list_documents(db: DbDep) -> ListDocumentsResponse:
    cursor = db[CollectionName.DOCUMENTS].find({}, {"raw_text": 0}).sort("_id", -1)
    items: list[DocumentListItem] = []
    async for raw in cursor:
        items.append(DocumentListItem.model_validate(mongo_doc_to_response(raw)))
    logger.info("DOCS  list  count=%d", len(items))
    return ListDocumentsResponse(documents=items)


@router.get("/{doc_id}", response_model=DocumentDetail)
async def get_document(doc_id: str, db: DbDep) -> DocumentDetail:
    """Return full document details including raw_text and summary."""
    oid = parse_object_id(doc_id, field="doc_id")
    doc = await db[CollectionName.DOCUMENTS].find_one({"_id": oid})
    if doc is None:
        raise ApiError(http_status=404, status="NOT_FOUND", message="Document not found.")
    logger.info("DOCS  get  doc_id=%s  title=%r", doc_id, doc.get("title", "")[:60])
    return DocumentDetail.model_validate(mongo_doc_to_response(doc))


@router.post("/{doc_id}/chat", response_model=ChatResponse)
async def chat_with_document(
    doc_id: str,
    body: ChatBody,
    db: DbDep,
) -> ChatResponse:
    """Ask the document_qa_agent a question about a specific document.

    Streams the response from ADK directly — no webhook roundtrip required.
    """
    if len(body.message) > settings.chat_max_message_chars:
        raise ApiError(
            http_status=400,
            status="INVALID_ARGUMENT",
            message=f"message exceeds {settings.chat_max_message_chars} characters.",
        )

    oid = parse_object_id(doc_id, field="doc_id")
    doc = await db[CollectionName.DOCUMENTS].find_one({"_id": oid})
    if doc is None:
        raise ApiError(http_status=404, status="NOT_FOUND", message="Document not found.")

    raw_text = doc.get("raw_text") or doc.get("summary") or ""
    context = raw_text[: settings.chat_max_context_chars]
    logger.info(
        "DOCS  chat  doc_id=%s  user_id=%s  history=%d turns  question=%r",
        doc_id,
        body.user_id or "anon",
        len(body.history),
        body.message[:80],
    )

    user_profile = None
    if body.user_id:
        try:
            from bson import ObjectId
            u = await db[CollectionName.USERS].find_one({"_id": ObjectId(body.user_id)})
            if u:
                user_profile = u.get("parsed_profile") or None
        except Exception:
            pass

    session_id = str(uuid.uuid4())
    history_dicts = [{"role": m.role, "text": m.text} for m in body.history]
    reply = await trigger_document_qa_agent(
        session_id=session_id,
        document_context=context,
        question=body.message,
        history=history_dicts or None,
        user_profile=user_profile,
    )
    logger.info("DOCS  chat  doc_id=%s  session=%s  reply_len=%d  context_chars=%d", doc_id, session_id, len(reply), len(context))
    return ChatResponse(reply=reply, context_chars_used=len(context))


@router.post("/{doc_id}/draft-comment", response_model=DraftCommentResponse)
async def draft_comment(
    doc_id: str,
    body: DraftCommentBody,
    db: DbDep,
) -> DraftCommentResponse:
    """Ask the draft_comment_agent to write a public comment letter.

    Streams the response from ADK directly.
    """
    oid = parse_object_id(doc_id, field="doc_id")
    doc = await db[CollectionName.DOCUMENTS].find_one({"_id": oid})
    if doc is None:
        raise ApiError(http_status=404, status="NOT_FOUND", message="Document not found.")

    summary = doc.get("summary") or doc.get("raw_text", "")[:1_000]
    session_id = str(uuid.uuid4())
    logger.info(
        "DOCS  draft  doc_id=%s  session=%s  user_id=%s  history=%d turns  ctx_len=%d",
        doc_id,
        session_id,
        body.user_id or "anon",
        len(body.history),
        len(body.resident_context),
    )

    user_profile = None
    if body.user_id:
        try:
            from bson import ObjectId
            u = await db[CollectionName.USERS].find_one({"_id": ObjectId(body.user_id)})
            if u:
                user_profile = u.get("parsed_profile") or None
        except Exception:
            pass

    history_dicts = [{"role": m.role, "text": m.text} for m in body.history]
    draft = await trigger_draft_comment_agent(
        session_id=session_id,
        document_summary=summary,
        conversation=history_dicts,
        resident_context=body.resident_context,
        user_profile=user_profile,
    )

    logger.info("DOCS  draft  doc_id=%s  session=%s  draft_len=%d", doc_id, session_id, len(draft))
    return DraftCommentResponse(draft_comment=draft)
