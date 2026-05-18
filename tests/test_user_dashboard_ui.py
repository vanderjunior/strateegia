from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


def create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), repository


def register_and_login(client: TestClient, username: str) -> None:
    registered = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "senha-segura-123",
            "display_name": username.title(),
            "email": f"{username}@example.com",
        },
    )
    assert registered.status_code == 201
    logged_in = client.post(
        "/api/auth/login",
        json={"username": username, "password": "senha-segura-123"},
    )
    assert logged_in.status_code == 200


def test_dashboard_ui_requires_auth_and_is_separate_from_root_and_inspection(tmp_path):
    owner, anonymous, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    unauth = anonymous.get("/dashboard")
    dashboard = owner.get("/dashboard")
    home = owner.get("/")
    inspection = owner.get("/inspection")
    dashboard_js = owner.get("/static/dashboard.js")
    dashboard_css = owner.get("/static/dashboard.css")

    assert unauth.status_code == 401
    assert dashboard.status_code == 200
    assert "Study Dashboard" in dashboard.text
    assert "read-only" in dashboard.text.lower()
    assert home.status_code == 200
    assert "Study Dashboard" not in home.text
    assert inspection.status_code == 200
    assert "Loading inspection payload" in inspection.text
    assert dashboard_js.status_code == 200
    assert dashboard_css.status_code == 200


def test_dashboard_ui_loads_even_when_user_has_no_artifacts(tmp_path):
    owner, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    response = owner.get("/dashboard")

    assert response.status_code == 200
    assert "Primary Next Step" in response.text
    assert "Pending Actions" in response.text
