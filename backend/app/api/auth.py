from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import DUMMY_HASH, create_access_token, verify_password
from app.db.session import get_db
from app.models.models import Organization, User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(
        select(User)
        .join(Organization, Organization.id == User.organization_id)
        .where(Organization.name == body.organization, User.username == body.username)
    )
    # Always verify something, so timing doesn't reveal whether the user exists.
    stored_hash = user.password_hash if user and user.password_hash else DUMMY_HASH
    password_ok = verify_password(body.password, stored_hash)

    if not (user and user.password_hash and user.is_active and password_ok):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(user.id, user.organization_id)
    return TokenResponse(access_token=token, expires_in=settings.access_token_expire_minutes * 60)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=user.id,
        organization_id=user.organization_id,
        username=user.username,
        department=user.department,
        roles=sorted(r.role_name for r in user.roles),
    )