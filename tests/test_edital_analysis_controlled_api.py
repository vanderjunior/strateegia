import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.ocr_documents import minimal_textual_pdf_bytes, ocr_required_pdf_result


ALLOWED_ANALYSIS_KEYS = {
    "edital_id",
    "document_id",
    "analysis_status",
    "review_state",
    "topics_count",
    "subtopics_count",
    "bibliography_count",
    "gaps_count",
    "warnings_count",
    "source",
}


FORBIDDEN_RESPONSE_TERMS = (
    "RAW-EDITAL-ANALYSIS-SHOULD-NOT-LEAK",
    "RAW-DOCUMENT-ANALYSIS-SHOULD-NOT-LEAK",
    "OTHER-USER-ANALYSIS-SHOULD-NOT-LEAK",
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


MINIMAL_STRUCTURED_EDITAL = b"""# EDITAL DE QA

## 1. CONTEUDO PROGRAMATICO

1. Lingua Portuguesa: Compreensao e interpretacao de textos; Ortografia oficial; Pontuacao.

2. Informatica: Redes de computadores; Seguranca da informacao; Banco de dados.

3. Direito Administrativo: Atos administrativos; Poderes administrativos; Responsabilidade civil do Estado.

## 2. BIBLIOGRAFIA

BRASIL. Constituicao da Republica Federativa do Brasil. 1988.
MANUAL DE QA. Referencia simulada para teste interno. 2026.
"""


SIMPLE_UNSTRUCTURED_EDITAL = (
    b"Conteudo programatico: Portugues, Informatica, Direito Administrativo. "
    b"Bibliografia: Constituicao Federal."
)

TEXTUAL_PDF_EDITAL = """EDITAL DE QA

1. CONTEUDO PROGRAMATICO

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

2. BIBLIOGRAFIA

BRASIL. Constituicao da Republica Federativa do Brasil. 1988.
MANUAL DE QA. Referencia simulada para teste interno. 2026.
"""


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
    filename: str = "edital.md",
    content: bytes | None = None,
    material_type: str = "edital",
    content_type: str = "text/markdown",
) -> dict[str, object]:
    payload = content or (
        b"# Conteudo Programatico\n\n"
        b"1. Arte Naval\n\n"
        b"2. Navegacao\n\n"
        b"# Bibliografia\n\n"
        b"Normas da Autoridade Maritima\n\n"
        b"RAW-EDITAL-ANALYSIS-SHOULD-NOT-LEAK"
    )
    uploaded = client.post(
        "/api/materials/upload",
        files={"file": (filename, BytesIO(payload), content_type)},
        data={"material_type": material_type},
    )
    assert uploaded.status_code == 201
    return uploaded.json()


def upload_and_process_edital(client: TestClient, *, filename: str = "edital.md") -> dict[str, object]:
    uploaded = upload_material(client, filename=filename, material_type="edital")
    document_id = uploaded["metadata"]["document_id"]
    processed = client.post(f"/api/materials/{document_id}/process")
    assert processed.status_code == 200
    return uploaded


def assert_no_forbidden_terms(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=False)
    for term in FORBIDDEN_RESPONSE_TERMS:
        assert term not in dumped


def assert_bounded_analysis_payload(payload: dict[str, object]) -> None:
    assert set(payload.keys()) == ALLOWED_ANALYSIS_KEYS
    assert payload["analysis_status"] in {"analyzed", "needs_review", "failed", "not_ready"}
    assert payload["review_state"] in {"ready_for_review", "needs_review", "pending", "unknown"}
    assert isinstance(payload["topics_count"], int)
    assert isinstance(payload["subtopics_count"], int)
    assert isinstance(payload["bibliography_count"], int)
    assert isinstance(payload["gaps_count"], int)
    assert isinstance(payload["warnings_count"], int)
    assert payload["source"] == "user_scope"
    assert_no_forbidden_terms(payload)


def test_controlled_edital_analysis_requires_auth(tmp_path):
    _, _, anonymous, _ = create_clients(tmp_path)

    response = anonymous.post("/api/materials/missing/edital/analyze")

    assert response.status_code == 401


def test_controlled_edital_analysis_returns_404_for_missing_document(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    response = owner.post("/api/materials/missing/edital/analyze")

    assert response.status_code == 404


def test_controlled_edital_analysis_is_user_scoped(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    uploaded = upload_and_process_edital(owner)
    document_id = uploaded["metadata"]["document_id"]

    response = other.post(f"/api/materials/{document_id}/edital/analyze")

    assert response.status_code == 404


def test_controlled_edital_analysis_pdf_is_user_scoped(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")
    uploaded = upload_material(
        owner,
        filename="edital-textual.pdf",
        material_type="edital",
        content=minimal_textual_pdf_bytes(TEXTUAL_PDF_EDITAL),
        content_type="application/pdf",
    )
    document_id = uploaded["metadata"]["document_id"]

    response = other.post(f"/api/materials/{document_id}/edital/analyze")

    assert response.status_code == 404


def test_controlled_edital_analysis_rejects_non_edital_material(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material(
        owner,
        filename="material.md",
        material_type="study_material",
        content=b"# Material de estudo\n\nConteudo suficiente para leitura segura.",
    )
    document_id = uploaded["metadata"]["document_id"]

    response = owner.post(f"/api/materials/{document_id}/edital/analyze")

    assert response.status_code == 422
    assert response.json()["detail"] == "Material is not classified as edital."


def test_controlled_edital_analysis_rejects_non_edital_pdf_material(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material(
        owner,
        filename="apostila.pdf",
        material_type="study_material",
        content=minimal_textual_pdf_bytes("Material de estudo com texto suficiente para leitura segura."),
        content_type="application/pdf",
    )
    document_id = uploaded["metadata"]["document_id"]

    response = owner.post(f"/api/materials/{document_id}/edital/analyze")

    assert response.status_code == 422
    assert response.json()["detail"] == "Material is not classified as edital."


def test_controlled_edital_analysis_returns_not_ready_without_safe_text(tmp_path, monkeypatch):
    owner, _, _, repository = create_clients(tmp_path)
    register_and_login(owner, "owner")

    def fail_if_ocr_runs(*args, **kwargs):
        raise AssertionError("Controlled edital analysis must not run OCR automatically.")

    monkeypatch.setattr("app.services.document_pipeline.extract_text_from_pdf", lambda _path: ocr_required_pdf_result())
    monkeypatch.setattr("app.services.document_pipeline.extract_text_with_ocr", fail_if_ocr_runs)
    uploaded = upload_material(
        owner,
        filename="edital.pdf",
        material_type="edital",
        content=b"%PDF-1.4 scanned",
        content_type="application/pdf",
    )
    document_id = uploaded["metadata"]["document_id"]

    response = owner.post(f"/api/materials/{document_id}/edital/analyze")
    payload = response.json()

    assert response.status_code == 200
    assert_bounded_analysis_payload(payload)
    assert payload["document_id"] == document_id
    assert payload["analysis_status"] == "not_ready"
    assert payload["review_state"] == "needs_review"
    extraction = repository.get_document_extraction_result(document_id, user_id=registered_user_id(owner))
    assert extraction is not None
    assert extraction.metadata["requires_ocr"] is True
    assert extraction.metadata["ocr_attempted"] is False


def registered_user_id(client: TestClient) -> str:
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    payload = me.json()
    assert payload["authenticated"] is True
    return payload["user"]["user_id"]


def test_controlled_edital_analysis_prepares_fresh_textual_pdf_without_ocr(tmp_path, monkeypatch):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    def fail_if_ocr_runs(*args, **kwargs):
        raise AssertionError("Controlled edital analysis must not run OCR automatically.")

    monkeypatch.setattr("app.services.document_pipeline.extract_text_with_ocr", fail_if_ocr_runs)
    uploaded = upload_material(
        owner,
        filename="edital-textual.pdf",
        material_type="edital",
        content=minimal_textual_pdf_bytes(TEXTUAL_PDF_EDITAL),
        content_type="application/pdf",
    )
    document_id = uploaded["metadata"]["document_id"]

    response = owner.post(f"/api/materials/{document_id}/edital/analyze")
    payload = response.json()

    assert response.status_code == 200
    assert_bounded_analysis_payload(payload)
    assert payload["document_id"] == document_id
    assert payload["analysis_status"] in {"analyzed", "needs_review"}
    assert payload["analysis_status"] != "not_ready"
    assert payload["topics_count"] >= 3
    assert payload["subtopics_count"] >= 9
    assert payload["bibliography_count"] >= 2

    repeated = owner.post(f"/api/materials/{document_id}/edital/analyze")
    assert repeated.status_code == 200
    assert repeated.json() == payload

    list_response = owner.get("/api/editais")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["count"] == 1
    assert [item["edital_id"] for item in list_payload["items"]] == [payload["edital_id"]]
    assert_no_forbidden_terms(list_payload)


def test_controlled_edital_analysis_prepares_fresh_unstructured_text_as_needs_review(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material(
        owner,
        filename="edital-simples.txt",
        material_type="edital",
        content=SIMPLE_UNSTRUCTURED_EDITAL,
        content_type="text/plain",
    )
    document_id = uploaded["metadata"]["document_id"]

    response = owner.post(f"/api/materials/{document_id}/edital/analyze")
    payload = response.json()

    assert response.status_code == 200
    assert_bounded_analysis_payload(payload)
    assert payload["document_id"] == document_id
    assert payload["analysis_status"] == "needs_review"
    assert payload["review_state"] == "needs_review"
    assert payload["topics_count"] == 0
    assert payload["subtopics_count"] == 0
    assert payload["bibliography_count"] == 0
    assert payload["warnings_count"] >= 1


def test_controlled_edital_analysis_prepares_and_analyzes_fresh_structured_markdown_fixture(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_material(
        owner,
        filename="edital-qa.md",
        material_type="edital",
        content=MINIMAL_STRUCTURED_EDITAL,
        content_type="text/markdown",
    )
    document_id = uploaded["metadata"]["document_id"]

    response = owner.post(f"/api/materials/{document_id}/edital/analyze")
    payload = response.json()

    assert response.status_code == 200
    assert_bounded_analysis_payload(payload)
    assert payload["document_id"] == document_id
    assert payload["edital_id"] == f"edital:{document_id}"
    assert payload["analysis_status"] == "analyzed"
    assert payload["review_state"] == "ready_for_review"
    assert payload["topics_count"] >= 3
    assert payload["subtopics_count"] >= 9
    assert payload["bibliography_count"] >= 2

    repeated = owner.post(f"/api/materials/{document_id}/edital/analyze")
    assert repeated.status_code == 200
    assert repeated.json() == payload

    list_response = owner.get("/api/editais")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["count"] == 1
    assert [item["edital_id"] for item in list_payload["items"]] == [payload["edital_id"]]


def test_controlled_edital_analysis_returns_bounded_success_and_populates_reads(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_and_process_edital(owner)
    document_id = uploaded["metadata"]["document_id"]

    response = owner.post(f"/api/materials/{document_id}/edital/analyze")
    payload = response.json()

    assert response.status_code == 200
    assert_bounded_analysis_payload(payload)
    assert payload["document_id"] == document_id
    assert payload["edital_id"] == f"edital:{document_id}"
    assert payload["analysis_status"] in {"analyzed", "needs_review"}
    assert payload["topics_count"] >= 1

    list_response = owner.get("/api/editais")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["count"] == 1
    assert list_payload["items"][0]["edital_id"] == payload["edital_id"]
    assert list_payload["items"][0]["analysis_status"] == payload["analysis_status"]
    assert_no_forbidden_terms(list_payload)

    summary_response = owner.get(f"/api/editais/{payload['edital_id']}/summary")
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload["edital_id"] == payload["edital_id"]
    assert summary_payload["analysis_status"] == payload["analysis_status"]
    assert_no_forbidden_terms(summary_payload)


def test_controlled_edital_analysis_repeated_call_is_safe_and_bounded(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    uploaded = upload_and_process_edital(owner)
    document_id = uploaded["metadata"]["document_id"]

    first = owner.post(f"/api/materials/{document_id}/edital/analyze").json()
    second = owner.post(f"/api/materials/{document_id}/edital/analyze").json()

    assert first == second
    assert_bounded_analysis_payload(first)
    assert first["edital_id"] == f"edital:{document_id}"
