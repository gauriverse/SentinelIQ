from functools import lru_cache

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection

from app.core.config import settings


@lru_cache
def get_client() -> MongoClient:
    return MongoClient(settings.mongo_url, tz_aware=True, serverSelectionTimeoutMS=3000)


def get_events_collection() -> Collection:
    """FastAPI dependency; tests override it with a throwaway collection."""
    return get_client()[settings.mongo_db]["events"]


def ensure_indexes(col: Collection) -> None:
    """Idempotent. Every index starts with organization_id: all queries are tenant-scoped."""
    col.create_index(
        [("organization_id", ASCENDING), ("event_id", ASCENDING)],
        unique=True, name="uq_org_event_id",
    )
    col.create_index(
        [("organization_id", ASCENDING), ("timestamp", DESCENDING)], name="ix_org_time"
    )
    col.create_index(
        [("organization_id", ASCENDING), ("user_id", ASCENDING), ("timestamp", DESCENDING)],
        name="ix_org_user_time",
    )
    col.create_index(
        [("organization_id", ASCENDING), ("event_type", ASCENDING), ("timestamp", DESCENDING)],
        name="ix_org_type_time",
    )