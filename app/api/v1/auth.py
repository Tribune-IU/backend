from fastapi import APIRouter

from app.api.deps import DbDep
from app.db.collections import CollectionName
from app.models.user import UserDocument
from app.schemas.v1 import AuthResponse

router = APIRouter(tags=["auth"])


@router.post("/auth", response_model=AuthResponse)
async def create_auth(db: DbDep) -> AuthResponse:
    """Create an anonymous user identity before onboarding.

    Returns a user_id the frontend should persist (e.g. localStorage).
    The user can later submit their bio via POST /v1/users/{user_id}/bio.
    """
    doc = UserDocument()
    payload = doc.model_dump(by_alias=True, exclude_none=True)
    payload.pop("_id", None)
    result = await db[CollectionName.USERS].insert_one(payload)
    return AuthResponse(user_id=str(result.inserted_id))
