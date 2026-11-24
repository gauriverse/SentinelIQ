from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pymongo.collection import Collection
from pymongo.errors import BulkWriteError, DuplicateKeyError

from app.schemas.events import EventIn, EventType

DUPLICATE_KEY = 11000


class DuplicateEventError(Exception):
    pass


def build_document(org_id: int, event: EventIn, received_at: datetime) -> dict[str, Any]:
    return {
        "event_id": event.event_id or f"evt_{uuid4().hex[:16]}",
        "organization_id": org_id,  # always from the authenticated user, never the payload
        "user_id": event.user_id,
        "event_type": event.event_type.value,
        "timestamp": event.timestamp,
        "source": event.source.model_dump() if event.source else None,
        "resource": event.resource.model_dump() if event.resource else None,
        "metadata": event.metadata,
        "source_type": event.source_type,
        "received_at": received_at,
    }


class EventRepository:
    def __init__(self, collection: Collection) -> None:
        self.col = collection

    def insert_one(self, org_id: int, event: EventIn) -> dict[str, Any]:
        doc = build_document(org_id, event, datetime.now(timezone.utc))
        try:
            self.col.insert_one(doc)
        except DuplicateKeyError as exc:
            raise DuplicateEventError(doc["event_id"]) from exc
        return doc

    def insert_many(self, org_id: int, events: list[EventIn]) -> tuple[int, int]:
        """Returns (inserted, duplicates). Duplicates are skipped, not fatal."""
        now = datetime.now(timezone.utc)
        docs = [build_document(org_id, e, now) for e in events]
        try:
            self.col.insert_many(docs, ordered=False)
        except BulkWriteError as exc:
            errors = exc.details.get("writeErrors", [])
            if any(e.get("code") != DUPLICATE_KEY for e in errors):
                raise
            return exc.details["nInserted"], len(errors)
        return len(docs), 0

    def search(
        self,
        org_id: int,
        *,
        user_id: int | None = None,
        event_type: EventType | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        query: dict[str, Any] = {"organization_id": org_id}
        if user_id is not None:
            query["user_id"] = user_id
        if event_type is not None:
            query["event_type"] = event_type.value
        if start or end:
            window: dict[str, datetime] = {}
            if start:
                window["$gte"] = start
            if end:
                window["$lt"] = end
            query["timestamp"] = window

        total = self.col.count_documents(query)
        cursor = (
            self.col.find(query)
            .sort([("timestamp", -1), ("_id", -1)])
            .skip(offset)
            .limit(limit)
        )
        return list(cursor), total