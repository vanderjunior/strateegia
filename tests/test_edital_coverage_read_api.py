import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


STRUCTURED_EDITAL = b"""# EDITAL DE QA

## 1. CONTEUDO PROGRAMATICO

Lingua Portuguesa:
1.1 Compreensao e interpretacao de textos.
1.2 Ortografia oficial.
1.3 Pontuacao.

Informatica:
2.1 Redes de computadores.
2.2 Seguranca da informacao.
2.3 Banco de dados.

Direito Administrativo:
3.1 Atos administrativos.
3.2 Poderes administrativos.
3.3 Responsabilidade civil do Estado.

## 2. BIBLIOGRAFIA

BRASIL. Constituicao da Republica Federativa do Brasil. 1988.
MANUAL DE QA. Referencia simulada para teste interno. 2026.
"""


ALLOWED_COVERAGE_KEYS = {
    "edital_id",
    "analysis_status",
    "coverage_status",
    "topics_count",
    "subtopics_count",
    "covered_subtopics_count",
    "partial_subtopics_count",
    "uncovered_subtopics_count",
    "out_of_scope_materials_count",
    "materials_considered_count",
    "items",
    "source",
}


ALLOWED_ITEM_KEYS = {
    "topic_id",
    "label",
    "subtopics_count",
    "covered_count",
    "partial_count",
    "uncovered_count",
    "status",
}


FORBIDDEN_RESPONSE_TERMS = (
    "RAW-EDITAL-COVERAGE-SHOULD-NOT-LEAK",
    "RAW-MATERIAL-COVERAGE-SHOULD-NOT-LEAK",
    "OTHER-COVERAGE-SHOULD-NOT-LEAK",
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
    "evidence",
    "raw_reference",
    "worker",
    "job trace",
)


def create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository


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


def upload_material(
    client: TestClient,
    *,
    filename: str,
    content: bytes,
    material_type: str = "study_material",
    content_type: str = "text/markdown",
) -> dict[str, object]:
    uploaded = client.post(
        "/api/materials/upload",
        files={"file": (filename, BytesIO(content), content_type)},
        data={"material_type": material_type},
    )
    assert uploaded.status_code == 201
    return uploaded.json()


def analyze_structured_edital(client: TestClient) -> dict[str, object]:
    uploaded = upload_material(
        client,
        filename="edital-qa.md",
        content=STRUCTURED_EDITAL,
        material_type="edital",
    )
    document_id = uploaded["metadata"]["document_id"]
    analyzed = client.post(f"/api/materials/{document_id}/edital/analyze")
    assert analyzed.status_code == 200
    payload = analyzed.json()
    assert payload["analysis_status"] == "analyzed"
    assert payload["subtopics_count"] >= 9
    return payload


def analyze_not_ready_edital(client: TestClient) -> dict[str, object]:
    uploaded = upload_material(
        client,
        filename="edital-curto.md",
        content=b"curto",
        material_type="edital",
    )
    document_id = uploaded["metadata"]["document_id"]
    analyzed = client.post(f"/api/materials/{document_id}/edital/analyze")
    assert analyzed.status_code == 200
    payload = analyzed.json()
    assert payload["analysis_status"] == "not_ready"
    return payload


def assert_no_forbidden_terms(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=False)
    for term in FORBIDDEN_RESPONSE_TERMS:
        assert term not in dumped


def assert_bounded_coverage_payload(payload: dict[str, object]) -> None:
    assert set(payload.keys()) == ALLOWED_COVERAGE_KEYS
    assert payload["analysis_status"] in {"analyzed", "needs_review", "failed", "not_ready", "unknown"}
    assert payload["coverage_status"] in {"not_ready", "partial", "ready_for_review", "needs_review", "unknown"}
    assert payload["source"] == "user_scope"
    assert isinstance(payload["topics_count"], int)
    assert isinstance(payload["subtopics_count"], int)
    assert isinstance(payload["covered_subtopics_count"], int)
    assert isinstance(payload["partial_subtopics_count"], int)
    assert isinstance(payload["uncovered_subtopics_count"], int)
    assert isinstance(payload["out_of_scope_materials_count"], int)
    assert isinstance(payload["materials_considered_count"], int)
    assert isinstance(payload["items"], list)
    for item in payload["items"]:
        assert set(item.keys()) == ALLOWED_ITEM_KEYS
        assert item["status"] in {"covered", "partial", "uncovered", "needs_review"}
    assert_no_forbidden_terms(payload)


def test_edital_coverage_requires_auth(tmp_path):
    _, _, anonymous, _ = create_clients(tmp_path)

    response = anonymous.get("/api/editais/edital:missing/coverage")

    assert response.status_code == 401


def test_edital_coverage_returns_404_for_missing_authenticated_item(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    response = owner.get("/api/editais/edital:missing/coverage")

    assert response.status_code == 404


def test_edital_coverage_is_user_scoped(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    owner_edital = analyze_structured_edital(owner)

    response = other.get(f"/api/editais/{owner_edital['edital_id']}/coverage")

    assert response.status_code == 404


def test_not_ready_edital_returns_not_ready_empty_coverage(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    edital = analyze_not_ready_edital(owner)

    response = owner.get(f"/api/editais/{edital['edital_id']}/coverage")
    payload = response.json()

    assert response.status_code == 200
    assert_bounded_coverage_payload(payload)
    assert payload["analysis_status"] == "not_ready"
    assert payload["coverage_status"] == "not_ready"
    assert payload["items"] == []
    assert payload["materials_considered_count"] == 0
    assert payload["covered_subtopics_count"] == 0
    assert payload["partial_subtopics_count"] == 0
    assert payload["uncovered_subtopics_count"] == 0


def test_analyzed_edital_with_no_materials_returns_uncovered_coverage(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    edital = analyze_structured_edital(owner)

    response = owner.get(f"/api/editais/{edital['edital_id']}/coverage")
    payload = response.json()

    assert response.status_code == 200
    assert_bounded_coverage_payload(payload)
    assert payload["analysis_status"] == "analyzed"
    assert payload["coverage_status"] == "needs_review"
    assert payload["topics_count"] == edital["topics_count"]
    assert payload["subtopics_count"] == edital["subtopics_count"]
    assert payload["materials_considered_count"] == 0
    assert payload["covered_subtopics_count"] == 0
    assert payload["partial_subtopics_count"] == 0
    assert payload["uncovered_subtopics_count"] == edital["subtopics_count"]
    assert len(payload["items"]) >= 3


def test_matching_study_material_metadata_returns_conservative_coverage(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    edital = analyze_structured_edital(owner)
    upload_material(
        owner,
        filename="compreensao-interpretacao-ortografia-pontuacao.md",
        content=b"# RAW-MATERIAL-COVERAGE-SHOULD-NOT-LEAK\n\nConteudo privado.",
        material_type="study_material",
    )

    response = owner.get(f"/api/editais/{edital['edital_id']}/coverage")
    payload = response.json()

    assert response.status_code == 200
    assert_bounded_coverage_payload(payload)
    assert payload["coverage_status"] in {"partial", "ready_for_review"}
    assert payload["materials_considered_count"] == 1
    assert payload["covered_subtopics_count"] + payload["partial_subtopics_count"] > 0
    portugues = next(item for item in payload["items"] if item["label"] == "Lingua Portuguesa")
    assert portugues["status"] in {"covered", "partial"}
    assert_no_forbidden_terms(payload)


def test_edital_source_and_unknown_material_do_not_falsely_cover(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    edital = analyze_structured_edital(owner)
    upload_material(
        owner,
        filename="compreensao-interpretacao-ortografia-pontuacao.md",
        content=b"# Material legado\n\nRAW-MATERIAL-COVERAGE-SHOULD-NOT-LEAK",
        material_type="unknown",
    )

    response = owner.get(f"/api/editais/{edital['edital_id']}/coverage")
    payload = response.json()

    assert response.status_code == 200
    assert_bounded_coverage_payload(payload)
    assert payload["materials_considered_count"] == 0
    assert payload["out_of_scope_materials_count"] == 1
    assert payload["covered_subtopics_count"] == 0
    assert payload["partial_subtopics_count"] == 0
    assert payload["uncovered_subtopics_count"] == edital["subtopics_count"]


def test_edital_coverage_repeated_get_is_idempotent(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    edital = analyze_structured_edital(owner)

    first = owner.get(f"/api/editais/{edital['edital_id']}/coverage").json()
    second = owner.get(f"/api/editais/{edital['edital_id']}/coverage").json()

    assert first == second
    assert_bounded_coverage_payload(first)
