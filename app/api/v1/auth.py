import logging
import re

from fastapi import APIRouter

from app.api.deps import DbDep
from app.db.collections import CollectionName
from app.models.user import UserDocument
from app.schemas.v1 import AuthBody, AuthResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])


@router.post("/auth", response_model=AuthResponse)
async def create_auth(body: AuthBody, db: DbDep) -> AuthResponse:
    """Sign in: reuse an existing user when the username matches, else create one.

    Password is ignored (dummy login). Username match is case-insensitive.
    Returns user_id to persist (e.g. localStorage).
    """
    name = body.username.strip()
    # Case-insensitive match so "alice" logs in as the same user as "Alice"
    escaped = re.escape(name)
    existing = await db[CollectionName.USERS].find_one(
        {"username": {"$regex": f"^{escaped}$", "$options": "i"}},
    )
    if existing is not None:
        user_id = str(existing["_id"])
        stored = (existing.get("username") or name).strip()
        logger.info("AUTH  existing user  user_id=%s  username=%s", user_id, stored)
        return AuthResponse(user_id=user_id, username=stored)

    doc = UserDocument(username=name)
    payload = doc.model_dump(by_alias=True, exclude_none=True)
    payload.pop("_id", None)
    result = await db[CollectionName.USERS].insert_one(payload)
    user_id = str(result.inserted_id)
    logger.info("AUTH  created user  user_id=%s  username=%s", user_id, name)
    return AuthResponse(user_id=user_id, username=name)
