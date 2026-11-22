from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("S3cret!pass")
    assert hashed != "S3cret!pass"
    assert verify_password("S3cret!pass", hashed)
    assert not verify_password("wrong", hashed)


def test_verify_password_handles_garbage_hash():
    assert not verify_password("anything", "not-a-hash")


def test_token_roundtrip():
    payload = decode_access_token(create_access_token(user_id=7, organization_id=3))
    assert payload["sub"] == "7"
    assert payload["org"] == 3


def test_expired_token_rejected():
    expired = jwt.encode(
        {"sub": "1", "org": 1, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired)


def test_tampered_token_rejected():
    token = create_access_token(1, 1)
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token[:-2] + "xx")