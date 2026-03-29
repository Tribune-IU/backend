import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from app.api.errors import register_exception_handlers
from app.api.v1.router import router as v1_router
from app.config import settings
from app.db.indexes import ensure_indexes
from app.services.seed_documents import ensure_seed_documents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Tribune API — connecting to MongoDB at %s / %s", settings.mongodb_uri, settings.mongodb_db_name)
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db_name]
    await ensure_indexes(db)
    await ensure_seed_documents(db)
    app.state.db = db
    app.state.mongo_client = client
    logger.info("Tribune API ready.")
    yield
    client.close()
    logger.info("Tribune API shut down.")


app = FastAPI(title="Tribune API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(v1_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    logger.info("%-6s %-45s → %d  (%.0f ms)", request.method, request.url.path, response.status_code, ms)
    return response


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
