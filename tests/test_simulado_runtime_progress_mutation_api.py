import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_runtime_progress_mutations import api_readonly_fixture


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


def prepare_explicit_apply(repository, tmp_path, user_id: str):
    fixture = api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)
    explicit_apply = fixture.explicit_apply
    assert explicit_apply is not None
    return explicit_apply


def test_runtime_progress_mutation_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    explicit_apply = prepare_explicit_apply(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-explicit-apply/{explicit_apply.explicit_apply_id}/progress-mutation")
    build = owner.post(
        f"/api/simulado-explicit-apply/{explicit_apply.explicit_apply_id}/progress-mutation/build"
    )
    loaded = owner.get(f"/api/simulado-explicit-apply/{explicit_apply.explicit_apply_id}/progress-mutation")
    mutation_id = build.json()["mutation_transaction_id"]
    by_id = owner.get(f"/api/simulado-progress-mutation/{mutation_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_explicit_apply_id"] == explicit_apply.explicit_apply_id
    assert loaded.json()["mutation_transaction_created"] is True
    assert loaded.json()["runtime_application_enabled"] is False
    assert loaded.json()["runtime_application_applied"] is False
    assert loaded.json()["progress_mutation_enabled"] is False
    assert loaded.json()["progress_mutation_applied"] is False
    assert loaded.json()["answer_key_publicly_exposed"] is False
    assert loaded.json()["gabarito_publicly_exposed"] is False
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert anonymous.post(
        f"/api/simulado-explicit-apply/{explicit_apply.explicit_apply_id}/progress-mutation/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-explicit-apply/{explicit_apply.explicit_apply_id}/progress-mutation"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-progress-mutation/{mutation_id}").status_code == 401


def test_runtime_progress_mutation_build_is_deterministic_and_owner_scoped(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    explicit_apply = prepare_explicit_apply(repository, tmp_path / "owner", owner_user_id)

    first = owner.post(
        f"/api/simulado-explicit-apply/{explicit_apply.explicit_apply_id}/progress-mutation/build"
    )
    second = owner.post(
        f"/api/simulado-explicit-apply/{explicit_apply.explicit_apply_id}/progress-mutation/build"
    )
    listed = repository.list_user_simulado_runtime_progress_mutation_transactions(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1

    mutation_id = first.json()["mutation_transaction_id"]
    assert other.post(
        f"/api/simulado-explicit-apply/{explicit_apply.explicit_apply_id}/progress-mutation/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-explicit-apply/{explicit_apply.explicit_apply_id}/progress-mutation"
    ).status_code == 404
    assert other.get(f"/api/simulado-progress-mutation/{mutation_id}").status_code == 404


def test_get_runtime_progress_mutation_is_read_only_and_missing_source_does_not_build(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    explicit_apply = prepare_explicit_apply(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-explicit-apply/{explicit_apply.explicit_apply_id}/progress-mutation")
    before_explicit = repository.get_simulado_explicit_runtime_apply_by_id(
        explicit_apply.explicit_apply_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-explicit-apply/{explicit_apply.explicit_apply_id}/progress-mutation/build"
    )
    loaded = owner.get(f"/api/simulado-explicit-apply/{explicit_apply.explicit_apply_id}/progress-mutation")
    after_explicit = repository.get_simulado_explicit_runtime_apply_by_id(
        explicit_apply.explicit_apply_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert before_explicit is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert after_explicit is not None
    assert before_explicit.model_dump(mode="json") == after_explicit.model_dump(mode="json")
