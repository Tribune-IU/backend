from fastapi import APIRouter, BackgroundTasks

from app.api.deps import DbDep
from app.api.errors import ApiError
from app.api.validation import parse_object_id
from app.db.collections import CollectionName
from app.db.mongo_utils import mongo_doc_to_response
from app.models.user import UserDocument
from app.schemas.v1 import AlertResource, CreateUserBody, CreateUserResponse, GetUserResponse, ListAlertsResponse, UserResource
from app.services.agents import trigger_profile_agent

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=CreateUserResponse)
async def create_user(body: CreateUserBody, db: DbDep, background_tasks: BackgroundTasks) -> CreateUserResponse:
    # 1. Create the user with an empty profile
    doc = UserDocument(bio=body.bio.strip(), parsed_profile={"location_zones": [], "roles": [], "interests": []})
    payload = doc.model_dump(by_alias=True, exclude_none=True)
    payload.pop("_id", None)
    result = await db[CollectionName.USERS].insert_one(payload)
    user_id = str(result.inserted_id)

    # 2. Trigger the agent which will call the webhook to save the profile (runs async)
    background_tasks.add_task(trigger_profile_agent, user_id, body.bio)

    # 3. Retrieve the inserted user immediately (profile tags will be empty until agent finishes)
    created = await db[CollectionName.USERS].find_one({"_id": result.inserted_id})
    if not created:
        raise ApiError(http_status=500, status="INTERNAL", message="Failed to load created user.")
    
    res = mongo_doc_to_response(created)
    return CreateUserResponse(user=UserResource.model_validate(res))


@router.get("/{user_id}", response_model=GetUserResponse)
async def get_user(user_id: str, db: DbDep) -> GetUserResponse:
    oid = parse_object_id(user_id, field="user_id")
    user = await db[CollectionName.USERS].find_one({"_id": oid})
    if user is None:
        raise ApiError(http_status=404, status="NOT_FOUND", message="User not found.")
    res = mongo_doc_to_response(user)
    return GetUserResponse(user=UserResource.model_validate(res))


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
