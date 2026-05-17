from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.user_service import LocalUserService


def create_client(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), repository


def test_create_and_load_user_hashes_password(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    service = LocalUserService(repository)

    user = service.register_user(
        username="ana",
        password="senha-segura-123",
        display_name="Ana",
        email="ana@example.com",
    )
    loaded = repository.get_user_by_username("ana")

    assert user.user_id
    assert loaded is not None
    assert loaded.username == "ana"
    assert loaded.display_name == "Ana"
    assert loaded.password_hash != "senha-segura-123"
    assert service.verify_password("senha-segura-123", loaded.password_hash) is True


def test_duplicate_user_is_rejected(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    service = LocalUserService(repository)
    service.register_user(username="ana", password="senha-segura-123", display_name="Ana")

    try:
        service.register_user(username="ana", password="outra-senha-123", display_name="Ana 2")
    except ValueError as exc:
        assert "already exists" in str(exc).lower()
    else:
        raise AssertionError("Expected duplicate user registration to fail.")


def test_login_me_logout_flow_uses_cookie_session(tmp_path):
    client, _ = create_client(tmp_path)

    registered = client.post(
        "/api/auth/register",
        json={
            "username": "marina",
            "password": "senha-segura-123",
            "display_name": "Marina",
            "email": "marina@example.com",
        },
    )
    logged_in = client.post(
        "/api/auth/login",
        json={"username": "marina", "password": "senha-segura-123"},
    )
    cookies_after_login = dict(client.cookies)
    me = client.get("/api/auth/me")
    logged_out = client.post("/api/auth/logout")
    me_after_logout = client.get("/api/auth/me")

    assert registered.status_code == 201
    assert logged_in.status_code == 200
    assert "studyflow_session" in cookies_after_login
    assert me.status_code == 200
    assert me.json()["authenticated"] is True
    assert me.json()["user"]["username"] == "marina"
    assert logged_out.status_code == 200
    assert me_after_logout.status_code == 200
    assert me_after_logout.json() == {"authenticated": False, "user": None}


def test_readme_and_requirements_cover_product_foundation_sections():
    requirements = Path("requirements.txt").read_text(encoding="utf-8").lower()
    readme = Path("README.md").read_text(encoding="utf-8").lower()

    assert "fastapi" in requirements
    assert "uvicorn" in requirements
    assert "python-multipart" in requirements
    assert "pytest" in requirements

    for section in [
        "como instalar",
        "como executar",
        "como rodar os testes",
        "upload",
        "limita",
        "inspection",
        "seguran",
        "roadmap",
    ]:
        assert section in readme
