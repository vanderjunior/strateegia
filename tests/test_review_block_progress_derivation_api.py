import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


FORBIDDEN_RESPONSE_TERMS = (
    "RAW-REVIEW-PROGRESS-SHOULD-NOT-LEAK",
    "extracted_text",
    "chunk body",
    "section body",
    "storage_path",
    "/Users/",
    "C:\\",
    "token",
    "cookie",
    "studyflow_session",
    "password_hash",
    "answer_key",
    "gabarito",
    "correct_answer",
    "correct_alternative",
    "score",
    "correction",
    "answer payload",
    "internal trace",
)

FORBIDDEN_WORDING = (
    "progresso atualizado",
    "material concluído",
    "você concluiu",
    "100%",
    "percentual",
    "pontuação",
    "resposta correta",
    "simulado",
)


def create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository


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


def upload_material(
    client: TestClient,
    *,
    filename: str,
    content: bytes,
    material_type: str = "study_material",
) -> dict[str, object]:
    uploaded = client.post(
        "/api/materials/upload",
        files={"file": (filename, BytesIO(content), "text/markdown")},
        data={"material_type": material_type},
    )
    assert uploaded.status_code == 201
    return uploaded.json()


def prepare_study_material(client: TestClient, uploaded: dict[str, object]) -> str:
    document_id = uploaded["metadata"]["document_id"]
    prepared = client.post(f"/api/materials/{document_id}/study/prepare")
    assert prepared.status_code == 200
    return str(document_id)


def upload_and_prepare_study_material(
    client: TestClient,
    index: int,
    *,
    sections: int = 1,
) -> str:
    if sections <= 1:
        content = (
            f"# Tema {index}\n\n"
            "RAW-REVIEW-PROGRESS-SHOULD-NOT-LEAK\n\n"
            "Conteudo seguro para estudo."
        ).encode("utf-8")
    else:
        content = (
            f"# Tema {index}\n\n"
            "Conteudo seguro para estudo.\n\n"
            f"## Subtema {index}\n\n"
            "Mais conteudo seguro para estudo."
        ).encode("utf-8")
    uploaded = upload_material(client, filename=f"progress-review-{index}.md", content=content)
    return prepare_study_material(client, uploaded)


def study_blocks(client: TestClient) -> list[dict[str, object]]:
    response = client.get("/api/study/blocks")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["items"], list)
    return payload["items"]


def block_ids_for_material(client: TestClient, document_id: str) -> list[str]:
    block_ids = [
        str(block["block_id"])
        for block in study_blocks(client)
        if block.get("material_id") == document_id
    ]
    assert block_ids
    return block_ids


def post_progress_event(
    client: TestClient,
    *,
    event_type: str,
    target_type: str,
    target_id: str,
    idempotency_key: str | None = None,
):
    payload = {
        "event_type": event_type,
        "target_type": target_type,
        "target_id": target_id,
    }
    if idempotency_key is not None:
        payload["idempotency_key"] = idempotency_key
    return client.post("/api/study/progress/events", json=payload)


def mark_block_studied(client: TestClient, block_id: str, *, key: str | None = None):
    response = post_progress_event(
        client,
        event_type="block_marked_studied",
        target_type="block",
        target_id=block_id,
        idempotency_key=key,
    )
    assert response.status_code == 200
    return response


def assert_no_forbidden_terms(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=False)
    lowered = dumped.lower()
    for term in FORBIDDEN_RESPONSE_TERMS:
        assert term not in dumped
    for term in FORBIDDEN_WORDING:
        assert term not in lowered


def assert_progress_summary(payload: dict[str, object]) -> None:
    assert set(payload.keys()) == {
        "progress_status",
        "opened_blocks_count",
        "studied_blocks_count",
        "prepared_materials_count",
        "studied_materials_count",
        "review_due",
        "review_basis",
        "reviewed_questions_count",
        "weak_topics_count",
        "source",
    }
    assert payload["review_basis"] in {"prepared_materials", "studied_materials", "none"}
    assert payload["source"] == "user_scope"
    assert_no_forbidden_terms(payload)


def assert_review_payload(payload: dict[str, object]) -> None:
    assert payload["basis"] in {"prepared_materials", "study_blocks", "studied_materials"}
    assert payload["source"] == "user_scope"
    assert_no_forbidden_terms(payload)


def test_progress_summary_does_not_derive_studied_materials_without_studied_blocks(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    document_id = upload_and_prepare_study_material(owner, 1)
    first_block_id = block_ids_for_material(owner, document_id)[0]
    assert post_progress_event(
        owner,
        event_type="block_opened",
        target_type="block",
        target_id=first_block_id,
    ).status_code == 200
    assert post_progress_event(
        owner,
        event_type="question_reviewed",
        target_type="question",
        target_id=f"question:{first_block_id}:0",
    ).status_code == 200

    payload = owner.get("/api/study/progress/summary").json()

    assert payload["opened_blocks_count"] == 1
    assert payload["reviewed_questions_count"] == 1
    assert payload["studied_blocks_count"] == 0
    assert payload["studied_materials_count"] == 0
    assert payload["review_basis"] == "none"
    assert_progress_summary(payload)


def test_one_block_material_becomes_studied_when_its_block_is_marked(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    document_id = upload_and_prepare_study_material(owner, 1)
    [block_id] = block_ids_for_material(owner, document_id)

    mark_block_studied(owner, block_id)
    payload = owner.get("/api/study/progress/summary").json()

    assert payload["studied_blocks_count"] == 1
    assert payload["studied_materials_count"] == 1
    assert payload["review_basis"] == "none"
    assert_progress_summary(payload)


def test_multi_block_material_requires_all_blocks_to_be_marked_studied(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    document_id = upload_and_prepare_study_material(owner, 1, sections=2)
    block_ids = block_ids_for_material(owner, document_id)
    assert len(block_ids) == 2

    mark_block_studied(owner, block_ids[0])
    partial = owner.get("/api/study/progress/summary").json()
    mark_block_studied(owner, block_ids[1])
    complete = owner.get("/api/study/progress/summary").json()

    assert partial["studied_blocks_count"] == 1
    assert partial["studied_materials_count"] == 0
    assert complete["studied_blocks_count"] == 2
    assert complete["studied_materials_count"] == 1
    assert_progress_summary(partial)
    assert_progress_summary(complete)


def test_progress_summary_falls_back_to_prepared_basis_until_three_materials_are_studied(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    document_ids = [upload_and_prepare_study_material(owner, index) for index in range(1, 4)]
    for document_id in document_ids[:2]:
        for block_id in block_ids_for_material(owner, document_id):
            mark_block_studied(owner, block_id)

    payload = owner.get("/api/study/progress/summary").json()
    review = owner.get("/api/study/review/next").json()

    assert payload["prepared_materials_count"] == 3
    assert payload["studied_materials_count"] == 2
    assert payload["review_due"] is True
    assert payload["review_basis"] == "prepared_materials"
    assert review["basis"] == "prepared_materials"
    assert review["materials_count"] == 3
    assert_progress_summary(payload)
    assert_review_payload(review)


def test_three_conservatively_studied_materials_switch_review_basis_to_studied_materials(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    document_ids = [upload_and_prepare_study_material(owner, index) for index in range(1, 4)]
    for document_id in document_ids:
        for block_id in block_ids_for_material(owner, document_id):
            mark_block_studied(owner, block_id)

    payload = owner.get("/api/study/progress/summary").json()
    review = owner.get("/api/study/review/next").json()

    assert payload["studied_blocks_count"] == 3
    assert payload["studied_materials_count"] == 3
    assert payload["review_due"] is True
    assert payload["review_basis"] == "studied_materials"
    assert review["basis"] == "studied_materials"
    assert review["materials_count"] == 3
    assert review["review_id"].startswith("review:studied_materials:")
    assert_progress_summary(payload)
    assert_review_payload(review)


def test_non_study_materials_and_other_users_do_not_count_as_studied_materials(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    for material_type in ("edital", "bibliography", "previous_exam", "note", "other", "unknown"):
        upload_material(
            owner,
            filename=f"{material_type}.md",
            content=b"# Arquivo de apoio\n\nConteudo seguro.",
            material_type=material_type,
        )
    document_id = upload_and_prepare_study_material(owner, 1)
    [block_id] = block_ids_for_material(owner, document_id)
    mark_block_studied(owner, block_id)

    owner_summary = owner.get("/api/study/progress/summary").json()
    other_summary = other.get("/api/study/progress/summary").json()

    assert owner_summary["prepared_materials_count"] == 1
    assert owner_summary["studied_materials_count"] == 1
    assert other_summary["prepared_materials_count"] == 0
    assert other_summary["studied_materials_count"] == 0
    assert_progress_summary(owner_summary)
    assert_progress_summary(other_summary)


def test_idempotent_duplicate_studied_block_event_does_not_double_count_materials(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    document_id = upload_and_prepare_study_material(owner, 1)
    [block_id] = block_ids_for_material(owner, document_id)

    first = mark_block_studied(owner, block_id, key=f"block_marked_studied:{block_id}")
    second = mark_block_studied(owner, block_id, key=f"block_marked_studied:{block_id}")
    payload = owner.get("/api/study/progress/summary").json()

    assert second.json() == first.json()
    assert payload["studied_blocks_count"] == 1
    assert payload["studied_materials_count"] == 1
    assert_progress_summary(payload)


def test_summary_and_review_reads_are_stable_and_do_not_create_progress_events(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    user = register_and_login(owner, "owner")
    for index in range(1, 4):
        document_id = upload_and_prepare_study_material(owner, index)
        for block_id in block_ids_for_material(owner, document_id):
            mark_block_studied(owner, block_id)

    before_events = repository.list_study_progress_events(user_id=str(user["user_id"]))
    first_summary = owner.get("/api/study/progress/summary").json()
    second_summary = owner.get("/api/study/progress/summary").json()
    first_review = owner.get("/api/study/review/next").json()
    second_review = owner.get("/api/study/review/next").json()
    after_events = repository.list_study_progress_events(user_id=str(user["user_id"]))

    assert first_summary == second_summary
    assert first_review == second_review
    assert after_events == before_events
    assert_progress_summary(first_summary)
    assert_review_payload(first_review)
