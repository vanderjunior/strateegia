import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


ALLOWED_ITEM_KEYS = {
    "document_id",
    "display_filename",
    "content_type",
    "material_type",
    "created_at",
    "updated_at",
    "processing_status",
    "extraction_status",
    "chunk_count",
    "section_count",
    "review_state",
    "warnings_count",
    "latest_pipeline_status",
}


FORBIDDEN_RESPONSE_TERMS = (
    "RAW-MATERIAL-BODY-SHOULD-NOT-LEAK",
    "OTHER-USER-SHOULD-NOT-LEAK",
    "extracted_text",
    "chunk body",
    "section body",
    "raw_ocr",
    "ocr_dump",
    "base64",
    "storage_path",
    "/Users/",
    "C:\\",
    "password_hash",
    "studyflow_session",
    "session token",
    "answer_key",
    "gabarito",
    "correctness",
    "is_correct",
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
    content_type: str = "text/markdown",
    material_type: str | None = None,
    process: bool = False,
) -> dict[str, object]:
    data = {"material_type": material_type} if material_type is not None else None
    uploaded = client.post(
        "/api/materials/upload",
        files={"file": (filename, BytesIO(content), content_type)},
        data=data,
    )
    assert uploaded.status_code == 201
    payload = uploaded.json()
    if process:
        processed = client.post(f"/api/materials/{payload['metadata']['document_id']}/process")
        assert processed.status_code == 200
    return payload


def assert_no_forbidden_terms(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=False)
    for term in FORBIDDEN_RESPONSE_TERMS:
        assert term not in dumped


def test_materials_list_requires_auth(tmp_path):
    _, _, anonymous, _ = create_clients(tmp_path)

    response = anonymous.get("/api/materials")

    assert response.status_code == 401


def test_materials_list_empty_for_authenticated_user(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "empty-user")

    response = owner.get("/api/materials")

    assert response.status_code == 200
    assert response.json() == {"items": [], "count": 0, "source": "user_scope"}


def test_materials_list_returns_own_bounded_uploaded_materials(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material(
        owner,
        filename="../../roteiro-praticagem.md",
        content=b"# Roteiro\n\nRAW-MATERIAL-BODY-SHOULD-NOT-LEAK",
        material_type="study_material",
        process=True,
    )
    document_id = uploaded["metadata"]["document_id"]

    response = owner.get("/api/materials")
    payload = response.json()

    assert response.status_code == 200
    assert payload["source"] == "user_scope"
    assert payload["count"] == 1
    assert len(payload["items"]) == payload["count"]
    item = payload["items"][0]
    assert set(item.keys()) == ALLOWED_ITEM_KEYS
    assert item["document_id"] == document_id
    assert item["display_filename"] == "roteiro-praticagem.md"
    assert item["content_type"] == "md"
    assert item["material_type"] == "study_material"
    assert item["chunk_count"] >= 1
    assert item["section_count"] >= 0
    assert item["latest_pipeline_status"]
    assert_no_forbidden_terms(payload)


def test_materials_list_preserves_uploaded_material_type_metadata(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "typed-owner")
    edital = upload_material(
        owner,
        filename="edital.md",
        content=b"# Edital\n\nConteudo seguro.",
        material_type="edital",
    )
    bibliography = upload_material(
        owner,
        filename="bibliografia.md",
        content=b"# Bibliografia\n\nReferencia segura.",
        material_type="bibliography",
    )
    legacy = upload_material(
        owner,
        filename="sem-tipo.md",
        content=b"# Sem tipo\n\nMaterial legado.",
    )

    response = owner.get("/api/materials")
    payload = response.json()
    items_by_id = {item["document_id"]: item for item in payload["items"]}

    assert response.status_code == 200
    assert items_by_id[edital["metadata"]["document_id"]]["material_type"] == "edital"
    assert items_by_id[bibliography["metadata"]["document_id"]]["material_type"] == "bibliography"
    assert items_by_id[legacy["metadata"]["document_id"]]["material_type"] == "unknown"
    assert_no_forbidden_terms(payload)


def test_materials_list_is_user_scoped(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    owner_upload = upload_material(
        owner,
        filename="owner-material.md",
        content=b"# Owner\n\nRAW-MATERIAL-BODY-SHOULD-NOT-LEAK",
        process=True,
    )
    other_upload = upload_material(
        other,
        filename="other-material.md",
        content=b"# Other\n\nOTHER-USER-SHOULD-NOT-LEAK",
        process=True,
    )

    owner_payload = owner.get("/api/materials").json()
    other_payload = other.get("/api/materials").json()

    owner_ids = {item["document_id"] for item in owner_payload["items"]}
    other_ids = {item["document_id"] for item in other_payload["items"]}
    assert owner_upload["metadata"]["document_id"] in owner_ids
    assert other_upload["metadata"]["document_id"] not in owner_ids
    assert other_upload["metadata"]["document_id"] in other_ids
    assert owner_upload["metadata"]["document_id"] not in other_ids
    assert_no_forbidden_terms(owner_payload)
    assert_no_forbidden_terms(other_payload)


def test_materials_list_shape_is_deterministic_and_bounded(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "stable-user")
    upload_material(owner, filename="a.txt", content=b"linha 1", content_type="text/plain")
    upload_material(owner, filename="b.pdf", content=b"%PDF-1.4", content_type="application/pdf")

    first = owner.get("/api/materials").json()
    second = owner.get("/api/materials").json()

    assert first == second
    assert first["count"] == len(first["items"])
    for item in first["items"]:
        assert set(item.keys()) == ALLOWED_ITEM_KEYS
        assert item["content_type"] in {"pdf", "txt", "md", "unknown"}
        assert item["material_type"] in {"edital", "study_material", "previous_exam", "bibliography", "note", "other", "unknown"}
        assert isinstance(item["chunk_count"], int)
        assert isinstance(item["section_count"], int)
        assert isinstance(item["warnings_count"], int)
    assert_no_forbidden_terms(first)
