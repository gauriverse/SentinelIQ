from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if creds is None:
        raise unauthorized
    try:
        payload = decode_access_token(creds.credentials)
        user_id = int(payload["sub"])
        org_id = int(payload["org"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized

    user = db.get(User, user_id)
    if user is None or not user.is_active or user.organization_id != org_id:
        raise unauthorized
    return user


def require_roles(*allowed: str) -> Callable[..., User]:
    """Dependency factory: user must hold at least one of the given roles."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if not {r.role_name for r in user.roles} & set(allowed):
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return checker