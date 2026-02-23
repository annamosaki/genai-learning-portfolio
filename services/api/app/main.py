from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .observability import flush_langfuse, init_langfuse, langfuse_status
from .routers import ask, floor, horizon, signal_desk, status, verdict

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_langfuse()
    yield
    flush_langfuse()


app = FastAPI(
    title="Anna Mosaki Portfolio API",
    version="1.0.0",
    description="Gateway for Year One demos with replay fallbacks and spend caps. Traced with Langfuse.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(status.router, prefix="/api")
app.include_router(verdict.router, prefix="/api/verdict")
app.include_router(horizon.router, prefix="/api/horizon")
app.include_router(signal_desk.router, prefix="/api/signal-desk")
app.include_router(floor.router, prefix="/api/floor")
app.include_router(ask.router, prefix="/api")


@app.get("/health")
def health():
    return {"ok": True, "observability": langfuse_status()}
