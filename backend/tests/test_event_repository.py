from datetime import datetime, timezone

import pytest

from app.repositories.events import DuplicateEventError, EventRepository
from app.schemas.events import EventIn, EventType


def ev(event_id=None, user_id=1, event_type="FILE_DOWNLOAD", ts="2026-11-21T10:00:00Z"):
    return EventIn(
        event_id=event_id, user_id=user_id, event_type=event_type, timestamp=ts
    )


def test_insert_and_search_roundtrip(events_col):
    repo = EventRepository(events_col)
    repo.insert_one(1, ev("e1"))
    items, total = repo.search(1)
    assert total == 1 and items[0]["event_id"] == "e1"


def test_organizations_are_isolated(events_col):
    repo = EventRepository(events_col)
    repo.insert_one(1, ev("e1"))
    items, total = repo.search(2)
    assert total == 0 and items == []


def test_same_event_id_allowed_in_different_orgs(events_col):
    repo = EventRepository(events_col)
    repo.insert_one(1, ev("shared"))
    repo.insert_one(2, ev("shared"))


def test_duplicate_event_raises(events_col):
    repo = EventRepository(events_col)
    repo.insert_one(1, ev("dup"))
    with pytest.raises(DuplicateEventError):
        repo.insert_one(1, ev("dup"))


def test_bulk_counts_duplicates(events_col):
    repo = EventRepository(events_col)
    repo.insert_one(1, ev("a"))
    inserted, dups = repo.insert_many(1, [ev("a"), ev("b"), ev("c"), ev("c")])
    assert (inserted, dups) == (2, 2)
    assert repo.search(1)[1] == 3


def test_filters_and_ordering(events_col):
    repo = EventRepository(events_col)
    repo.insert_many(1, [
        ev("e1", 1, "LOGIN_FAILED", "2026-11-21T09:00:00Z"),
        ev("e2", 1, "FILE_DOWNLOAD", "2026-11-21T10:00:00Z"),
        ev("e3", 2, "FILE_DOWNLOAD", "2026-11-21T11:00:00Z"),
    ])
    items, total = repo.search(1, event_type=EventType.FILE_DOWNLOAD)
    assert [i["event_id"] for i in items] == ["e3", "e2"]  # newest first
    items, _ = repo.search(1, user_id=1)
    assert {i["event_id"] for i in items} == {"e1", "e2"}
    start = datetime(2026, 11, 21, 9, 30, tzinfo=timezone.utc)
    items, _ = repo.search(1, start=start)
    assert {i["event_id"] for i in items} == {"e2", "e3"}


def test_pagination(events_col):
    repo = EventRepository(events_col)
    repo.insert_many(1, [ev(f"e{i}", ts=f"2026-11-21T10:0{i}:00Z") for i in range(5)])
    items, total = repo.search(1, limit=2, offset=2)
    assert total == 5
    assert [i["event_id"] for i in items] == ["e2", "e1"]


def test_expected_indexes_exist(events_col):
    names = set(events_col.index_information())
    assert {"uq_org_event_id", "ix_org_time", "ix_org_user_time", "ix_org_type_time"} <= names