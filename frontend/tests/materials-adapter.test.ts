import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

vi.mock("@/lib/api/documents", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/documents")>("@/lib/api/documents");

  return {
    ...actual,
    fetchUserMaterialsList: vi.fn()
  };
});

import {
  buildMockMaterialDetail,
  buildMockMaterialsWorkspaceViewModel,
  loadMaterialsWorkspaceViewModel
} from "@/lib/adapters/materials";
import { getApiConfig } from "@/lib/api/config";
import { fetchUserMaterialsList } from "@/lib/api/documents";

describe("materials adapter", () => {
  beforeEach(() => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
    vi.mocked(fetchUserMaterialsList).mockReset();
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
      expect(item.processingStatus).toBeTruthy();
      expect(item.extractionStatus).toBeTruthy();
      expect(item.reviewState).toBeTruthy();
      expect(item.source).toBeTruthy();
    });
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

  it("uses real authenticated materials metadata when available", async () => {
    vi.mocked(fetchUserMaterialsList).mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        total_materials: 1,
        processed_count: 1,
        pending_count: 0,
        ocr_required_count: 0,
        items: [
          {
            document_id: "doc-1",
            display_filename: "roteiro-porto.pdf",
            content_type: "application/pdf",
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
          }
        ]
      } as never
    });

    const viewModel = await loadMaterialsWorkspaceViewModel();
    const payload = JSON.stringify(viewModel);

    expect(viewModel.connection.title).toBe("Dados reais da sessão");
    expect(viewModel.items).toHaveLength(1);
    expect(viewModel.items[0]).toMatchObject({
      id: "doc-1",
      title: "roteiro-porto",
      typeLabel: "PDF textual",
      processingStatus: "Material processado",
      extractionStatus: "Texto extraído",
      reviewState: "Pronto para revisão",
      source: "backend",
      sectionsCount: 4,
      chunksCount: 12
    });
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

  it("shows backend offline and keeps safe fallback when the backend is unreachable", async () => {
    vi.mocked(fetchUserMaterialsList).mockResolvedValue({
      ok: false,
      status: 502,
      source: "offline",
      error: {
        code: "backend_offline",
        message: "Não foi possível conectar ao backend."
      }
    });

    const viewModel = await loadMaterialsWorkspaceViewModel();

    expect(viewModel.connection.title).toBe("Backend offline");
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
});
