import json
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from ipaddress import ip_address
from typing import Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

MAX_METADATA_KEYS = 30
MAX_METADATA_BYTES = 8_192
MAX_CLOCK_SKEW = timedelta(minutes=5)


class EventType(StrEnum):
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    FILE_ACCESS = "FILE_ACCESS"
    FILE_DOWNLOAD = "FILE_DOWNLOAD"
    PERMISSION_CHANGE = "PERMISSION_CHANGE"
    RESOURCE_ACCESS = "RESOURCE_ACCESS"
    USB_CONNECT = "USB_CONNECT"

class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ip: str | None = None
    device: str | None = Field(default=None, max_length=128)

    @field_validator("ip")
    @classmethod
    def _valid_ip(cls, v: str | None) -> str | None:
        return None if v is None else str(ip_address(v))


class Resource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = Field(max_length=50)
    id: str = Field(max_length=128)


class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")  # rejects e.g. organization_id

    event_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_\-]{1,64}$")
    user_id: int
    event_type: EventType
    timestamp: AwareDatetime
    source: Source | None = None
    resource: Resource | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_type: Literal["simulated", "real", "dataset"] = "simulated"

    @field_validator("timestamp")
    @classmethod
    def _utc_and_not_future(cls, v: datetime) -> datetime:
        if v > datetime.now(timezone.utc) + MAX_CLOCK_SKEW:
            raise ValueError("timestamp is in the future")
        return v.astimezone(timezone.utc)

    @field_validator("metadata")
    @classmethod
    def _check_metadata(cls, v: dict[str, Any]) -> dict[str, Any]:
        if len(v) > MAX_METADATA_KEYS:
            raise ValueError(f"metadata has more than {MAX_METADATA_KEYS} keys")

        def walk(obj: Any) -> None:
            if isinstance(obj, dict):
                for key, val in obj.items():
                    k = str(key)
                    if k.startswith("$") or "." in k:
                        raise ValueError(f"invalid metadata key: {k!r}")
                    walk(val)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)

        walk(v)
        if len(json.dumps(v, default=str)) > MAX_METADATA_BYTES:
            raise ValueError("metadata is too large")
        return v


class BulkEventsIn(BaseModel):
    events: list[EventIn] = Field(min_length=1, max_length=1000)


class EventOut(BaseModel):
    event_id: str
    user_id: int
    event_type: EventType
    timestamp: datetime
    source: Source | None = None
    resource: Resource | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_type: str
    received_at: datetime


class EventPage(BaseModel):
    items: list[EventOut]
    total: int
    limit: int
    offset: int


class BulkResult(BaseModel):
    received: int
    inserted: int
    duplicates: int