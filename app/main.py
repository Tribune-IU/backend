from contextlib import asynccontextmanager

from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

from app.api.errors import register_exception_handlers
from app.api.v1.router import router as v1_router
from app.config import settings
from app.db.indexes import ensure_indexes
from app.services.seed_documents import ensure_seed_documents


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]
    await ensure_indexes(db)
    await ensure_seed_documents(db)
    app.state.db = db
    app.state.mongo_client = client
    yield
    client.close()


app = FastAPI(title="Tribune API", version="0.1.0", lifespan=lifespan)
register_exception_handlers(app)

app.include_router(v1_router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
