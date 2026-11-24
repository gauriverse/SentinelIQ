from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo.collection import Collection
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.mongo import get_events_collection
from app.db.session import get_db
from app.models.models import User
from app.repositories.events import DuplicateEventError, EventRepository
from app.schemas.events import (
    BulkEventsIn, BulkResult, EventIn, EventOut, EventPage, EventType,
)

router = APIRouter(prefix="/api/v1/events", tags=["events"])


def existing_user_ids(db: Session, org_id: int, ids: set[int]) -> set[int]:
    return set(db.scalars(select(User.id).where(User.organization_id == org_id, User.id.in_(ids))))


def _require_known_users(db: Session, org_id: int, ids: set[int]) -> None:
    unknown = ids - existing_user_ids(db, org_id, ids)
    if unknown:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown user_id for this organization: {sorted(unknown)[:10]}",
        )


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def ingest_event(
    body: EventIn,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
    col: Collection = Depends(get_events_collection),
) -> EventOut:
    _require_known_users(db, user.organization_id, {body.user_id})
    try:
        doc = EventRepository(col).insert_one(user.organization_id, body)
    except DuplicateEventError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Event already ingested")
    return EventOut.model_validate(doc)


@router.post("/bulk", response_model=BulkResult)
def ingest_events_bulk(
    body: BulkEventsIn,
    user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
    col: Collection = Depends(get_events_collection),
) -> BulkResult:
    _require_known_users(db, user.organization_id, {e.user_id for e in body.events})
    inserted, duplicates = EventRepository(col).insert_many(user.organization_id, body.events)
    return BulkResult(received=len(body.events), inserted=inserted, duplicates=duplicates)


@router.get("", response_model=EventPage)
def list_events(
    user_id: int | None = None,
    event_type: EventType | None = None,
    start: datetime | None = Query(None, description="Inclusive, ISO 8601 (UTC if no offset)"),
    end: datetime | None = Query(None, description="Exclusive, ISO 8601 (UTC if no offset)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=100_000),
    user: User = Depends(require_roles("admin", "analyst", "viewer")),
    col: Collection = Depends(get_events_collection),
) -> EventPage:
    start_utc, end_utc = _as_utc(start), _as_utc(end)
    if start_utc and end_utc and start_utc >= end_utc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start must be before end")
    docs, total = EventRepository(col).search(
        user.organization_id,
        user_id=user_id, event_type=event_type,
        start=start_utc, end=end_utc, limit=limit, offset=offset,
    )
    return EventPage(
        items=[EventOut.model_validate(d) for d in docs],
        total=total, limit=limit, offset=offset,
    )