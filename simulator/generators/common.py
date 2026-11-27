from datetime import datetime, timezone
from typing import Any


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class IdFactory:
    """Deterministic, readable event IDs: <prefix>_<n>."""

    def __init__(self, prefix: str) -> None:
        self.prefix, self.n = prefix, 0

    def next(self) -> str:
        self.n += 1
        return f"{self.prefix}_{self.n}"


def make_event(
    event_id: str,
    user_id: int,
    event_type: str,
    ts: datetime,
    ip: str,
    device: str,
    resource: tuple[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "event_id": event_id,
        "user_id": user_id,
        "event_type": event_type,
        "timestamp": iso(ts),
        "source": {"ip": ip, "device": device},
        "metadata": metadata or {},
        "source_type": "simulated",
    }
    if resource:
        event["resource"] = {"type": resource[0], "id": resource[1]}
    return event