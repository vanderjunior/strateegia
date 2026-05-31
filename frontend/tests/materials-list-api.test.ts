import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

import { fetchMaterialSummary, fetchUserMaterialsList, prepareStudyMaterial } from "@/lib/api/documents";
import { getApiConfig } from "@/lib/api/config";

describe("materials list API wrapper", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
  });

  it("does not attempt protected read in mock mode", async () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: true
    });
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = await fetchUserMaterialsList();

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("mock_mode");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it.each([
    [401, "unauthorized", "Sessão necessária."],
    [403, "unauthorized", "Sessão necessária."],
    [502, "backend_offline", "Não foi possível carregar os dados agora."],
    [503, "missing_base_url", "A listagem real de materiais não está configurada neste ambiente."]
  ])("maps HTTP %i to %s", async (status, code, message) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await fetchUserMaterialsList();

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe(code);
    expect(result.error.message).toBe(message);
  });

  it("returns the safe materials list payload on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            total_materials: 1,
            processed_count: 1,
            pending_count: 0,
            ocr_required_count: 0,
            items: [
              {
                document_id: "doc-1",
                display_filename: "roteiro-porto.pdf",
                content_type: "pdf",
                material_type: "edital",
                status: "ready_for_review",
                uploaded_at: "2026-05-27T00:00:00Z",
                extraction_status: "textual_pdf",
                current_stage: "metadata_ready",
                metadata_status: "ready",
                chunk_count: 12,
                section_count: 4
              }
            ]
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchUserMaterialsList();

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data.items[0].document_id).toBe("doc-1");
    expect(result.data.items[0].material_type).toBe("edital");
    expect(JSON.stringify(result.data)).not.toContain("token");
    expect(JSON.stringify(result.data)).not.toContain("cookie");
  });

  it.each([
    [401, "unauthorized", "Sessão necessária."],
    [403, "unauthorized", "Sessão necessária."],
    [404, "not_found", "Este conteúdo não está disponível nesta sessão."],
    [502, "backend_offline", "Não foi possível carregar os dados agora."],
    [503, "missing_base_url", "O resumo real do material não está configurado neste ambiente."]
  ])("maps material summary HTTP %i to %s", async (status, code, message) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await fetchMaterialSummary("doc-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe(code);
    expect(result.error.message).toBe(message);
  });

  it("returns the bounded material summary payload on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            document_id: "doc-1",
            display_filename: "roteiro.pdf",
            content_type: "pdf",
            material_type: "bibliography",
            created_at: "2026-05-27T00:00:00Z",
            updated_at: "2026-05-27T00:05:00Z",
            processing_status: "ready_for_review",
            extraction_status: "textual_pdf",
            review_state: "ready_for_review",
            chunk_count: 12,
            section_count: 4,
            warnings_count: 1,
            latest_pipeline_status: "metadata_ready",
            pipeline: {
              status: "metadata_ready",
              steps_count: 4,
              has_ocr_warning: false,
              ready_for_review: true
            },
            source: "user_scope"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchMaterialSummary("doc-1");

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data.document_id).toBe("doc-1");
    expect(result.data.material_type).toBe("bibliography");
    expect(result.data.pipeline.ready_for_review).toBe(true);
    expect(JSON.stringify(result.data)).not.toContain("token");
    expect(JSON.stringify(result.data)).not.toContain("cookie");
  });

  it.each([
    [401, "auth_required", "Entre para preparar este material."],
    [403, "auth_required", "Entre para preparar este material."],
    [404, "not_found", "Material não encontrado nesta sessão."],
    [422, "invalid_material_type", "Este arquivo não está classificado como material de estudo."],
    [502, "backend_offline", "Não foi possível preparar o material agora."],
    [503, "missing_base_url", "A preparação do material não está configurada neste ambiente."]
  ])("maps study material preparation HTTP %i to %s", async (status, code, message) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await prepareStudyMaterial("doc-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe(code);
    expect(result.error.message).toBe(message);
  });

  it("returns the bounded study material preparation payload on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            document_id: "doc-1",
            preparation_status: "ready_for_study",
            material_type: "study_material",
            section_count: 4,
            chunk_count: 12,
            warnings_count: 0,
            ready_for_study: true,
            source: "user_scope",
            extracted_text: "RAW-SHOULD-NOT-LEAK",
            storage_path: "/Users/private/aula.md",
            token: "TOKEN-SHOULD-NOT-LEAK"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await prepareStudyMaterial("doc-1");

    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data).toMatchObject({
      document_id: "doc-1",
      preparation_status: "ready_for_study",
      material_type: "study_material",
      section_count: 4,
      chunk_count: 12,
      ready_for_study: true
    });
    expect(JSON.stringify(result.data)).not.toContain("extracted_text");
    expect(JSON.stringify(result.data)).not.toContain("storage_path");
    expect(JSON.stringify(result.data)).not.toContain("TOKEN-SHOULD-NOT-LEAK");
  });

  it("maps invalid study preparation shape to invalid_response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ document_id: "doc-1", preparation_status: "surprise" }), {
          status: 200,
          headers: { "content-type": "application/json" }
        })
      )
    );

    const result = await prepareStudyMaterial("doc-1");

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("invalid_response");
  });
});
