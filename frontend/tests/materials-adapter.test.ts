import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

vi.mock("@/lib/api/documents", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/documents")>("@/lib/api/documents");

  return {
    ...actual,
    fetchMaterialSummary: vi.fn(),
    fetchUserMaterialsList: vi.fn()
  };
});

import {
  buildMockMaterialDetail,
  buildMockMaterialsWorkspaceViewModel,
  loadMaterialDetail,
  loadMaterialsWorkspaceViewModel
} from "@/lib/adapters/materials";
import { getApiConfig } from "@/lib/api/config";
import { fetchMaterialSummary, fetchUserMaterialsList } from "@/lib/api/documents";

describe("materials adapter", () => {
  beforeEach(() => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
    vi.mocked(fetchUserMaterialsList).mockReset();
    vi.mocked(fetchMaterialSummary).mockReset();
  });

  it("returns a mock-first materials workspace with expected demo items", () => {
    const viewModel = buildMockMaterialsWorkspaceViewModel();
    const titles = viewModel.items.map((item) => item.title);

    expect(viewModel.connection.title).toContain("demonstração");
    expect(titles.some((title) => title.includes("Arte Naval"))).toBe(true);
    expect(titles.some((title) => title.includes("Shiphandling"))).toBe(true);
    expect(titles.some((title) => title.includes("Roteiro escaneado"))).toBe(true);

    viewModel.items.forEach((item) => {
      expect(item.title).toBeTruthy();
      expect(item.typeLabel).toBeTruthy();
      expect(item.materialType).toBeTruthy();
      expect(item.materialTypeLabel).toBeTruthy();
      expect(item.processingStatus).toBeTruthy();
      expect(item.extractionStatus).toBeTruthy();
      expect(item.reviewState).toBeTruthy();
      expect(item.source).toBeTruthy();
    });
    expect(viewModel.materialTypeGroups.find((group) => group.type === "bibliography")?.count).toBe(1);
    expect(viewModel.materialTypeGroups.find((group) => group.type === "study_material")?.count).toBe(2);
    expect(viewModel.hasStudyMaterial).toBe(true);
    expect(viewModel.hasEdital).toBe(false);
  });

  it("returns safe detail previews and OCR warnings without raw content", () => {
    const scanned = buildMockMaterialDetail("material-roteiro-porto");
    const textual = buildMockMaterialDetail("material-arte-naval");
    expect(scanned).not.toBeNull();
    expect(textual).not.toBeNull();
    const payload = JSON.stringify({ scanned, textual });

    expect(scanned?.warnings.some((warning) => warning.includes("OCR"))).toBe(true);
    expect(scanned?.sectionPreviews.every((section) => Boolean(section.title))).toBe(true);
    expect(textual?.sectionPreviews.every((section) => Boolean(section.chunkRangeLabel))).toBe(true);

    expect(payload).not.toContain(["raw", "document", "body"].join(" "));
    expect(payload).not.toContain(["raw", "OCR", "text", "dump"].join(" "));
    expect(payload).not.toContain(["base", "64"].join(""));
    expect(payload).not.toContain("/Users/");
    expect(payload).not.toContain(["gaba", "rito"].join(""));
  });

  it("returns null for an unknown material detail id", () => {
    expect(buildMockMaterialDetail("material-desconhecido")).toBeNull();
  });

  it("uses real authenticated materials metadata and groups by material type when available", async () => {
    vi.mocked(fetchUserMaterialsList).mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        total_materials: 3,
        processed_count: 1,
        pending_count: 2,
        ocr_required_count: 0,
        items: [
          {
            document_id: "doc-1",
            display_filename: "roteiro-porto.pdf",
            content_type: "application/pdf",
            material_type: "previous_exam",
            status: "metadata_ready",
            uploaded_at: "2026-05-27T00:00:00Z",
            extraction_status: "extracted",
            current_stage: "metadata_ready",
            metadata_status: "ready",
            chunk_count: 12,
            section_count: 4,
            source_excerpt: "não deve aparecer",
            extracted_text: "não deve aparecer",
            storage_path: "uploads/user-x/doc-1.pdf"
          },
          {
            document_id: "doc-2",
            display_filename: "edital-pscpp.pdf",
            content_type: "application/pdf",
            material_type: "edital",
            status: "uploaded",
            uploaded_at: "2026-05-27T00:00:00Z",
            extraction_status: "pending",
            current_stage: "uploaded",
            metadata_status: "not_ready",
            chunk_count: 0,
            section_count: 0
          },
          {
            document_id: "doc-3",
            display_filename: "sem-tipo.txt",
            content_type: "text/plain",
            material_type: "unexpected",
            status: "uploaded",
            uploaded_at: "2026-05-27T00:00:00Z",
            extraction_status: "pending",
            current_stage: "uploaded",
            metadata_status: "not_ready",
            chunk_count: 0,
            section_count: 0
          }
        ]
      } as never
    });

    const viewModel = await loadMaterialsWorkspaceViewModel();
    const payload = JSON.stringify(viewModel);

    expect(viewModel.connection.title).toBe("Informações da sua conta");
    expect(viewModel.items).toHaveLength(3);
    expect(viewModel.items[0]).toMatchObject({
      id: "doc-1",
      title: "roteiro-porto",
      typeLabel: "PDF textual",
      materialTypeLabel: "Prova anterior",
      processingStatus: "Material processado",
      extractionStatus: "Texto extraído",
      reviewState: "Pronto para revisão",
      source: "backend",
      sectionsCount: 4,
      chunksCount: 12
    });
    expect(viewModel.hasEdital).toBe(true);
    expect(viewModel.hasStudyMaterial).toBe(false);
    expect(viewModel.unclassifiedCount).toBe(1);
    expect(viewModel.materialTypeGroups.find((group) => group.type === "previous_exam")?.count).toBe(1);
    expect(viewModel.materialTypeGroups.find((group) => group.type === "edital")?.count).toBe(1);
    expect(viewModel.materialTypeGroups.find((group) => group.type === "unknown")?.items[0].materialTypeLabel).toBe(
      "Tipo não informado"
    );
    expect(payload).not.toContain("source_excerpt");
    expect(payload).not.toContain("extracted_text");
    expect(payload).not.toContain("storage_path");
  });

  it("shows requires session and keeps demo fallback when unauthenticated", async () => {
    vi.mocked(fetchUserMaterialsList).mockResolvedValue({
      ok: false,
      status: 401,
      source: "backend",
      error: {
        code: "unauthorized",
        message: "Sessão necessária."
      }
    });

    const viewModel = await loadMaterialsWorkspaceViewModel();

    expect(viewModel.connection.title).toBe("Requer sessão");
    expect(viewModel.items.length).toBeGreaterThan(0);
    expect(viewModel.items.some((item) => item.source === "mock")).toBe(true);
  });

  it("shows unavailable data and keeps safe fallback when the backend is unreachable", async () => {
    vi.mocked(fetchUserMaterialsList).mockResolvedValue({
      ok: false,
      status: 502,
      source: "offline",
      error: {
        code: "backend_offline",
        message: "Não foi possível carregar os dados agora."
      }
    });

    const viewModel = await loadMaterialsWorkspaceViewModel();

    expect(viewModel.connection.title).toBe("Dados indisponíveis");
    expect(viewModel.items.length).toBeGreaterThan(0);
    expect(viewModel.items.some((item) => item.source === "mock")).toBe(true);
  });

  it("does not attempt protected read in forced mock mode", async () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: true
    });

    const viewModel = await loadMaterialsWorkspaceViewModel();

    expect(viewModel.connection.title).toContain("demonstração");
    expect(fetchUserMaterialsList).not.toHaveBeenCalled();
  });

  it("uses real bounded material summary for authenticated detail", async () => {
    vi.mocked(fetchMaterialSummary).mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        document_id: "doc-1",
        display_filename: "roteiro-porto.pdf",
        content_type: "application/pdf",
        material_type: "study_material",
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
        source: "user_scope",
        extracted_text: "não deve aparecer",
        raw_chunks: [{ body: "não deve aparecer" }],
        storage_path: "/Users/private/upload.pdf"
      } as never
    });

    const viewModel = await loadMaterialDetail("doc-1");
    const payload = JSON.stringify(viewModel);

    expect(viewModel.connection.title).toBe("Informações da sua conta");
    expect(viewModel.connection.endpoint).toBe("/api/materials/doc-1/summary");
    expect(viewModel.detail).toMatchObject({
      id: "doc-1",
      title: "roteiro-porto",
      typeLabel: "PDF textual",
      materialTypeLabel: "Material de estudo",
      processingStatus: "Material processado",
      extractionStatus: "Texto extraído",
      reviewState: "Pronto para revisão",
      sectionsCount: 4,
      chunksCount: 12,
      source: "backend"
    });
    expect(payload).not.toContain("extracted_text");
    expect(payload).not.toContain("raw_chunks");
    expect(payload).not.toContain("storage_path");
    expect(payload).not.toContain("/Users/");
  });

  it("keeps safe fallback when material summary requires session", async () => {
    vi.mocked(fetchMaterialSummary).mockResolvedValue({
      ok: false,
      status: 401,
      source: "backend",
      error: {
        code: "unauthorized",
        message: "Sessão necessária."
      }
    });

    const viewModel = await loadMaterialDetail("material-arte-naval");

    expect(viewModel.connection.title).toBe("Requer sessão");
    expect(viewModel.detail?.source).toBe("mock");
  });

  it("returns friendly not-found state when material summary is outside the session", async () => {
    vi.mocked(fetchMaterialSummary).mockResolvedValue({
      ok: false,
      status: 404,
      source: "backend",
      error: {
        code: "not_found",
        message: "Este conteúdo não está disponível nesta sessão."
      }
    });

    const viewModel = await loadMaterialDetail("doc-fora-da-sessao");

    expect(viewModel.connection.title).toBe("Item não encontrado");
    expect(viewModel.detail).toBeNull();
  });
});
