from types import SimpleNamespace

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, require_roles
from app.main import app as main_app

app = FastAPI()


@app.get("/admin-only")
def admin_only(user=Depends(require_roles("admin"))):
    return {"ok": True}


@app.get("/staff")
def staff(user=Depends(require_roles("admin", "analyst"))):
    return {"ok": True}


def as_user(*roles: str) -> TestClient:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        roles=[SimpleNamespace(role_name=r) for r in roles]
    )
    return TestClient(app)


def test_admin_allowed_on_admin_route():
    assert as_user("admin").get("/admin-only").status_code == 200


def test_viewer_forbidden_on_admin_route():
    assert as_user("viewer").get("/admin-only").status_code == 403


def test_any_listed_role_is_enough():
    assert as_user("analyst").get("/staff").status_code == 200
    assert as_user("viewer").get("/staff").status_code == 403


def test_me_requires_token():
    assert TestClient(main_app).get("/api/v1/auth/me").status_code == 401