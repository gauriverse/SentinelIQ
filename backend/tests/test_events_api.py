from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import events as events_api
from app.api.deps import get_current_user
from app.db.mongo import get_events_collection
from app.db.session import get_db
from app.main import app


def payload(**overrides):
    base = {
        "user_id": 1,
        "event_type": "FILE_DOWNLOAD",
        "timestamp": "2026-11-21T15:30:00Z",
        "source": {"ip": "192.168.1.25", "device": "device_01"},
        "resource": {"type": "document", "id": "doc_204"},
        "metadata": {"file_size_mb": 450, "department": "Finance"},
    }
    base.update(overrides)
    return base


@pytest.fixture
def make_client(events_col, monkeypatch):
    # Pretend users 1..99 exist, so these tests don't need PostgreSQL.
    monkeypatch.setattr(
        events_api, "existing_user_ids", lambda db, org, ids: {i for i in ids if i < 100}
    )

    def _make(org_id: int = 1, roles: tuple[str, ...] = ("admin",)) -> TestClient:
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            id=1, organization_id=org_id,
            roles=[SimpleNamespace(role_name=r) for r in roles],
        )
        app.dependency_overrides[get_events_collection] = lambda: events_col
        app.dependency_overrides[get_db] = lambda: None
        return TestClient(app)

    yield _make
    app.dependency_overrides.clear()


def test_ingest_stores_event_under_token_org(make_client, events_col):
    res = make_client(org_id=7).post("/api/v1/events", json=payload(event_id="evt_1"))
    assert res.status_code == 201
    assert res.json()["event_id"] == "evt_1"
    assert events_col.find_one({"event_id": "evt_1"})["organization_id"] == 7


def test_event_id_generated_when_missing(make_client):
    res = make_client().post("/api/v1/events", json=payload())
    assert res.json()["event_id"].startswith("evt_")


def test_duplicate_returns_409(make_client):
    client = make_client()
    assert client.post("/api/v1/events", json=payload(event_id="d1")).status_code == 201
    assert client.post("/api/v1/events", json=payload(event_id="d1")).status_code == 409


def test_unknown_user_returns_422(make_client):
    assert make_client().post("/api/v1/events", json=payload(user_id=500)).status_code == 422


def test_body_cannot_choose_organization(make_client):
    res = make_client().post("/api/v1/events", json=payload(organization_id=99))
    assert res.status_code == 422


def test_viewer_cannot_ingest_but_can_read(make_client):
    client = make_client(roles=("viewer",))
    assert client.post("/api/v1/events", json=payload()).status_code == 403
    assert client.get("/api/v1/events").status_code == 200


def test_bulk_reports_duplicates(make_client):
    client = make_client()
    body = {"events": [payload(event_id="b1"), payload(event_id="b2"), payload(event_id="b1")]}
    res = client.post("/api/v1/events/bulk", json=body)
    assert res.json() == {"received": 3, "inserted": 2, "duplicates": 1}


def test_other_org_cannot_see_events(make_client):
    make_client(org_id=1).post("/api/v1/events", json=payload())
    res = make_client(org_id=2, roles=("viewer",)).get("/api/v1/events")
    assert res.json()["total"] == 0


def test_filtering_and_pagination(make_client):
    client = make_client()
    events = [
        payload(event_id=f"p{i}", timestamp=f"2026-11-21T10:0{i}:00Z",
                event_type="LOGIN_FAILED" if i % 2 else "FILE_DOWNLOAD")
        for i in range(5)
    ]
    client.post("/api/v1/events/bulk", json={"events": events})
    res = client.get("/api/v1/events", params={"event_type": "LOGIN_FAILED"})
    assert res.json()["total"] == 2
    res = client.get("/api/v1/events", params={"limit": 2, "offset": 1})
    assert [e["event_id"] for e in res.json()["items"]] == ["p3", "p2"]


def test_query_validation(make_client):
    client = make_client()
    assert client.get("/api/v1/events", params={"limit": 0}).status_code == 422
    assert client.get("/api/v1/events", params={"limit": 5000}).status_code == 422
    assert client.get("/api/v1/events", params={"event_type": "NOPE"}).status_code == 422