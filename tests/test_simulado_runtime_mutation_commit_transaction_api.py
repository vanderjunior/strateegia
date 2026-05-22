import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_runtime_mutation_commit_transactions import (
    api_readonly_fixture,
)


def create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository


def register_and_login(client: TestClient, username: str) -> str:
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
    return logged_in.json()["user"]["user_id"]


def prepare_explicit_commit(repository, tmp_path, user_id: str):
    fixture = api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)
    explicit_commit = fixture.explicit_commit
    assert explicit_commit is not None
    return explicit_commit


def test_runtime_mutation_commit_transaction_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    explicit_commit = prepare_explicit_commit(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction")
    build = owner.post(
        f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction/build"
    )
    loaded = owner.get(f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction")
    commit_transaction_id = build.json()["commit_transaction_id"]
    by_id = owner.get(f"/api/simulado-commit-transaction/{commit_transaction_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_explicit_commit_id"] == explicit_commit.explicit_commit_id
    assert loaded.json()["commit_transaction_created"] is True
    assert loaded.json()["commit_transaction_valid_for_execution"] is False
    assert loaded.json()["commit_executed"] is False
    assert loaded.json()["mutation_committed"] is False
    assert loaded.json()["runtime_application_enabled"] is False
    assert loaded.json()["progress_mutation_enabled"] is False
    assert loaded.json()["answer_key_publicly_exposed"] is False
    assert loaded.json()["gabarito_publicly_exposed"] is False
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert anonymous.post(
        f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-commit-transaction/{commit_transaction_id}").status_code == 401


def test_runtime_mutation_commit_transaction_build_is_deterministic_for_same_source(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    explicit_commit = prepare_explicit_commit(repository, tmp_path / "owner", owner_user_id)

    first = owner.post(
        f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction/build"
    )
    second = owner.post(
        f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction/build"
    )
    listed = repository.list_user_simulado_runtime_mutation_commit_transactions(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_runtime_mutation_commit_transaction(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    explicit_commit = prepare_explicit_commit(repository, tmp_path / "owner", owner_user_id)
    build = owner.post(
        f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction/build"
    )
    assert build.status_code == 200
    commit_transaction_id = build.json()["commit_transaction_id"]

    assert other.post(
        f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction"
    ).status_code == 404
    assert other.get(f"/api/simulado-commit-transaction/{commit_transaction_id}").status_code == 404


def test_get_runtime_mutation_commit_transaction_is_read_only_and_missing_source_does_not_build(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    explicit_commit = prepare_explicit_commit(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction")
    before_explicit = repository.get_simulado_explicit_mutation_commit_by_id(
        explicit_commit.explicit_commit_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction/build"
    )
    loaded = owner.get(f"/api/simulado-explicit-commit/{explicit_commit.explicit_commit_id}/commit-transaction")
    after_explicit = repository.get_simulado_explicit_mutation_commit_by_id(
        explicit_commit.explicit_commit_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert before_explicit is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert after_explicit is not None
    assert before_explicit.model_dump(mode="json") == after_explicit.model_dump(mode="json")
