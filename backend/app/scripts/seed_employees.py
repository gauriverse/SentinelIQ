"""Create simulated monitored employees (no password). Safe to re-run."""
import os

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.models import Organization, User

DEPARTMENTS = ["Engineering", "Finance", "HR", "Sales", "Support"]


def main() -> None:
    org_name = os.getenv("SEED_ORG", "Acme Corp")
    count = int(os.getenv("SEED_EMPLOYEES", "50"))

    with SessionLocal() as db:
        org = db.scalar(select(Organization).where(Organization.name == org_name))
        if org is None:
            raise SystemExit(f"Organization '{org_name}' not found. Run app.scripts.seed first.")
        existing = set(db.scalars(select(User.username).where(User.organization_id == org.id)))
        created = 0
        for i in range(1, count + 1):
            username = f"emp{i:03d}"
            if username not in existing:
                db.add(User(
                    organization_id=org.id,
                    username=username,
                    department=DEPARTMENTS[(i - 1) % len(DEPARTMENTS)],
                ))
                created += 1
        db.commit()
        print(f"Created {created} employees ({count - created} already existed)")


if __name__ == "__main__":
    main()