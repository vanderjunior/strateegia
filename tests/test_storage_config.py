from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_studyflow_data_file, get_studyflow_upload_root
from app.main import create_app


def register_and_login(client: TestClient, username: str) -> dict[str, object]:
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
    return registered.json()


def test_default_storage_paths_are_preserved(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATA_DIR", raising=False)
    monkeypatch.delenv("STUDYFLOW_DATA_FILE", raising=False)
    monkeypatch.delenv("STUDYFLOW_UPLOAD_ROOT", raising=False)

    app = create_app()

    assert get_studyflow_data_file() == Path("data") / "study_data.json"
    assert get_studyflow_upload_root() == Path("data") / "uploads"
    assert app.state.repository.path == Path("data") / "study_data.json"
    assert app.state.storage_root == Path("data") / "uploads"
    assert (tmp_path / "data" / "study_data.json").exists()


def test_data_dir_drives_default_staging_persistent_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "railway-data"
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.delenv("STUDYFLOW_DATA_FILE", raising=False)
    monkeypatch.delenv("STUDYFLOW_UPLOAD_ROOT", raising=False)

    app = create_app()

    assert get_studyflow_data_file() == data_dir / "study_data.json"
    assert get_studyflow_upload_root() == data_dir / "uploads"
    assert app.state.repository.path == data_dir / "study_data.json"
    assert app.state.storage_root == data_dir / "uploads"
    assert app.state.repository.path.exists()


def test_env_configured_data_file_and_upload_root_are_used(tmp_path, monkeypatch):
    data_file = tmp_path / "state" / "study_data.json"
    upload_root = tmp_path / "persistent_uploads"
    monkeypatch.setenv("STUDYFLOW_DATA_FILE", str(data_file))
    monkeypatch.setenv("STUDYFLOW_UPLOAD_ROOT", str(upload_root))

    app = create_app()

    assert app.state.repository.path == data_file
    assert app.state.storage_root == upload_root
    assert data_file.exists()
    assert upload_root.is_absolute()
    assert "/Users/" not in str(app.state.repository.path)
    assert "/Users/" not in str(app.state.storage_root)


def test_upload_uses_env_configured_upload_root(tmp_path, monkeypatch):
    data_file = tmp_path / "state" / "study_data.json"
    upload_root = tmp_path / "uploads-volume"
    monkeypatch.setenv("STUDYFLOW_DATA_FILE", str(data_file))
    monkeypatch.setenv("STUDYFLOW_UPLOAD_ROOT", str(upload_root))
    app = create_app()
    client = TestClient(app)
    user = register_and_login(client, "storage-user")

    response = client.post(
        "/api/materials/upload",
        files={"file": ("roteiro.txt", BytesIO(b"linha 1"), "text/plain")},
    )
    payload = response.json()

    assert response.status_code == 201
    assert payload["metadata"]["storage_path"].startswith(f"uploads/{user['user_id']}/")
    stored_files = list((upload_root / user["user_id"]).glob("*_roteiro.txt"))
    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == b"linha 1"
