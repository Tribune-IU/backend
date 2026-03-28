from fastapi import APIRouter

from app.api.deps import DbDep
from app.api.errors import ApiError
from app.api.validation import parse_object_id
from app.config import settings
from app.db.collections import CollectionName
from app.db.mongo_utils import mongo_doc_to_response
from app.schemas.v1 import ChatBody, ChatResponse, DocumentListItem, ListDocumentsResponse

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=ListDocumentsResponse)
async def list_documents(db: DbDep) -> ListDocumentsResponse:
    cursor = db[CollectionName.DOCUMENTS].find({}, {"raw_text": 0}).sort("_id", -1)
    items: list[DocumentListItem] = []
    async for raw in cursor:
        items.append(DocumentListItem.model_validate(mongo_doc_to_response(raw)))
    return ListDocumentsResponse(documents=items)


@router.post("/{doc_id}/chat", response_model=ChatResponse)
async def chat_with_document(doc_id: str, body: ChatBody, db: DbDep) -> ChatResponse:
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

    raw_text = doc.get("raw_text") or ""
    context = raw_text[: settings.chat_max_context_chars]
    snippet = body.message.strip().replace("\n", " ")[:500]
    reply = (
        "(Stub assistant) This endpoint does not call an LLM yet. "
        f"Your question: “{snippet}”. "
        f"The server loaded the first {len(context)} characters of the document text as context. "
        "For the demo, Manish’s agent can replace this with grounded answers and citations."
    )
    return ChatResponse(reply=reply, context_chars_used=len(context))
