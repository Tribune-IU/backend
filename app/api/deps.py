from typing import Annotated

from fastapi import Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase


def get_db(request: Request) -> AsyncIOMotorDatabase:
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise RuntimeError("Database is not initialized")
    return db


DbDep = Annotated[AsyncIOMotorDatabase, Depends(get_db)]
