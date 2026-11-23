import pytest
from pydantic import ValidationError

from app.schemas.events import EventIn


def make(**overrides):
    base = {
        "user_id": 1,
        "event_type": "FILE_DOWNLOAD",
        "timestamp": "2026-11-21T15:30:00+05:30",
        "source": {"ip": "192.168.1.25", "device": "device_01"},
        "resource": {"type": "document", "id": "doc_204"},
        "metadata": {"file_size_mb": 450},
    }
    base.update(overrides)
    return base


def test_valid_event_is_normalised_to_utc():
    event = EventIn(**make())
    assert event.timestamp.utcoffset().total_seconds() == 0
    assert event.timestamp.hour == 10 and event.timestamp.minute == 0


def test_naive_timestamp_rejected():
    with pytest.raises(ValidationError):
        EventIn(**make(timestamp="2026-11-21T15:30:00"))


def test_future_timestamp_rejected():
    with pytest.raises(ValidationError):
        EventIn(**make(timestamp="2999-01-01T00:00:00Z"))


def test_invalid_ip_rejected():
    with pytest.raises(ValidationError):
        EventIn(**make(source={"ip": "999.1.1.1"}))


def test_unknown_event_type_rejected():
    with pytest.raises(ValidationError):
        EventIn(**make(event_type="DELETE_EVERYTHING"))


@pytest.mark.parametrize("bad_key", ["$where", "a.b"])
def test_dangerous_metadata_keys_rejected(bad_key):
    with pytest.raises(ValidationError):
        EventIn(**make(metadata={"ok": {bad_key: 1}}))


def test_oversized_metadata_rejected():
    with pytest.raises(ValidationError):
        EventIn(**make(metadata={"blob": "x" * 9000}))


def test_client_cannot_set_organization():
    with pytest.raises(ValidationError):
        EventIn(**make(organization_id=99))