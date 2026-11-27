from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.models import User
from app.schemas.users import MonitoredUser, UserPage

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=UserPage)
def list_monitored_users(
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_roles("admin", "analyst", "viewer")),
    db: Session = Depends(get_db),
) -> UserPage:
    """Monitored employees: active users without login credentials, in the caller's org."""
    where = (
        User.organization_id == user.organization_id,
        User.password_hash.is_(None),
        User.is_active.is_(True),
    )
    total = db.scalar(select(func.count()).select_from(User).where(*where)) or 0
    rows = db.scalars(select(User).where(*where).order_by(User.id).limit(limit).offset(offset))
    return UserPage(
        items=[MonitoredUser(id=u.id, username=u.username, department=u.department) for u in rows],
        total=total, limit=limit, offset=offset,
    )