from fastapi import APIRouter

from app.api.deps import DbDep
from app.api.errors import ApiError
from app.api.validation import parse_object_id
from app.db.collections import CollectionName
from app.db.mongo_utils import mongo_doc_to_response
from app.models.user import UserDocument
from app.schemas.v1 import AlertResource, CreateUserBody, CreateUserResponse, ListAlertsResponse, UserResource
from app.services.mock_profile import mock_parsed_profile_from_bio

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=CreateUserResponse)
async def create_user(body: CreateUserBody, db: DbDep) -> CreateUserResponse:
    parsed = mock_parsed_profile_from_bio(body.bio)
    doc = UserDocument(bio=body.bio.strip(), parsed_profile=parsed)
    payload = doc.model_dump(by_alias=True, exclude_none=True)
    payload.pop("_id", None)
    result = await db[CollectionName.USERS].insert_one(payload)
    created = await db[CollectionName.USERS].find_one({"_id": result.inserted_id})
    if not created:
        raise ApiError(http_status=500, status="INTERNAL", message="Failed to load created user.")
    res = mongo_doc_to_response(created)
    return CreateUserResponse(user=UserResource.model_validate(res))


@router.get("/{user_id}/alerts", response_model=ListAlertsResponse)
async def list_user_alerts(user_id: str, db: DbDep) -> ListAlertsResponse:
    oid = parse_object_id(user_id, field="user_id")
    user = await db[CollectionName.USERS].find_one({"_id": oid})
    if user is None:
        raise ApiError(http_status=404, status="NOT_FOUND", message="User not found.")

    cursor = db[CollectionName.ALERTS].find({"user_id": user_id, "is_active": True}).sort("_id", -1)
    alerts: list[AlertResource] = []
    async for raw in cursor:
        data = mongo_doc_to_response(raw)
        alerts.append(AlertResource.model_validate(data))
    return ListAlertsResponse(alerts=alerts)
