from contextlib import asynccontextmanager

from fastapi import FastAPI


from app.api import auth, events
from app.core.config import settings
from app.db.mongo import ensure_indexes, get_events_collection
from app.api import auth, events, users

@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_indexes(get_events_collection())
    yield

app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(users.router)

@app.get("/health", tags=["system"])
def health() -> dict[str,str]:
    return {"status":"ok", "version": settings.version}