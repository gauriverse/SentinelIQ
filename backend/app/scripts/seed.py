import getpass
import os

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.models import Organization, Role, User

ROLE_NAMES = ["admin", "analyst", "viewer"]


def main() -> None:
    org_name = os.getenv("SEED_ORG", "Acme Corp")
    username = os.getenv("SEED_ADMIN_USERNAME", "admin")
    password = os.getenv("SEED_ADMIN_PASSWORD") or getpass.getpass("Admin password: ")
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters")

    with SessionLocal() as db:
        roles: dict[str, Role] = {}
        for name in ROLE_NAMES:
            role = db.scalar(select(Role).where(Role.role_name == name))
            if role is None:
                role = Role(role_name=name)
                db.add(role)
            roles[name] = role

        org = db.scalar(select(Organization).where(Organization.name == org_name))
        if org is None:
            org = Organization(name=org_name)
            db.add(org)
        db.flush()  # assigns IDs

        user = db.scalar(
            select(User).where(User.organization_id == org.id, User.username == username)
        )
        if user is None:
            user = User(
                organization_id=org.id,
                username=username,
                department="Security",
                password_hash=hash_password(password),
            )
            user.roles.append(roles["admin"])
            db.add(user)
            print(f"Created admin '{username}' in organization '{org_name}'")
        else:
            print(f"User '{username}' already exists, nothing changed")
        db.commit()


if __name__ == "__main__":
    main()