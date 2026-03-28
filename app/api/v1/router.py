from fastapi import APIRouter

from app.api.v1 import documents, system, users

router = APIRouter(prefix="/v1")
router.include_router(users.router)
router.include_router(documents.router)
router.include_router(system.router)
