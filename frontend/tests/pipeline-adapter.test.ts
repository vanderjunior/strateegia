import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

vi.mock("@/lib/api/pipeline", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/pipeline")>("@/lib/api/pipeline");

  return {
    ...actual,
    fetchPipelineSummary: vi.fn()
  };
});

import { buildMockPipelineDetail, loadPipelineDetail } from "@/lib/adapters/pipeline";
import { getApiConfig } from "@/lib/api/config";
import { fetchPipelineSummary } from "@/lib/api/pipeline";

describe("pipeline adapter", () => {
  beforeEach(() => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
    vi.mocked(fetchPipelineSummary).mockReset();
  });

  it("returns read-only user-facing timeline steps", () => {
    const textual = buildMockPipelineDetail("material-arte-naval");
    const scanned = buildMockPipelineDetail("material-roteiro-porto");
    expect(textual).not.toBeNull();
    expect(scanned).not.toBeNull();

    expect(textual?.steps.map((step) => step.label)).toEqual(
      expect.arrayContaining(["Enviado", "Texto extraído", "Segmentado", "Pronto para revisão"])
    );
    expect(scanned?.steps.some((step) => step.statusLabel.includes("OCR"))).toBe(true);
  });

  it("does not expose backend internals, raw text, or process actions", () => {
    const payload = JSON.stringify({
      textual: buildMockPipelineDetail("material-arte-naval"),
      scanned: buildMockPipelineDetail("material-roteiro-porto")
    });

    expect(payload).not.toContain("chunking_status");
    expect(payload).not.toContain("sectioning_status");
    expect(payload).not.toContain(["raw", "OCR", "text", "dump"].join(" "));
    expect(payload).not.toContain(["raw", "document", "body"].join(" "));
    expect(payload).not.toContain(["base", "64"].join(""));
    expect(payload).not.toContain("Processar");
    expect(payload).not.toContain("Reprocessar");
  });

  it("returns null for an unknown pipeline detail id", () => {
    expect(buildMockPipelineDetail("pipeline-desconhecido")).toBeNull();
  });

  it("uses real bounded pipeline summary for authenticated detail", async () => {
    vi.mocked(fetchPipelineSummary).mockResolvedValue({
      ok: true,
      status: 200,
      source: "backend",
      data: {
        document_id: "doc-1",
        status: "ready_for_review",
        steps: [
          {
            key: "uploaded",
            label: "Enviado",
            state: "done",
            warnings_count: 0
          },
          {
            key: "text_extracted",
            label: "Texto extraído",
            state: "done",
            warnings_count: 0
          },
          {
            key: "segmented",
            label: "Segmentado",
            state: "done",
            warnings_count: 0
          },
          {
            key: "ready_for_review",
            label: "Pronto para revisão",
            state: "done",
            warnings_count: 0
          }
        ],
        steps_count: 4,
        has_ocr_warning: false,
        ready_for_review: true,
        section_count: 4,
        chunk_count: 12,
        warnings_count: 0,
        source: "user_scope",
        extracted_text: "não deve aparecer",
        raw_chunks: [{ body: "não deve aparecer" }],
        worker_trace: "não deve aparecer"
      } as never
    });

    const viewModel = await loadPipelineDetail("doc-1");
    const payload = JSON.stringify(viewModel);

    expect(viewModel.connection.title).toBe("Dados reais da sessão");
    expect(viewModel.connection.endpoint).toBe("/api/materials/doc-1/pipeline/summary");
    expect(viewModel.detail).toMatchObject({
      documentId: "doc-1",
      source: "backend",
      extractionStatus: "Texto extraído",
      reviewState: "Pronto para revisão",
      sectionsCount: 4,
      chunksCount: 12
    });
    expect(viewModel.detail?.steps.map((step) => step.label)).toEqual([
      "Enviado",
      "Texto extraído",
      "Segmentado",
      "Pronto para revisão"
    ]);
    expect(payload).not.toContain("extracted_text");
    expect(payload).not.toContain("raw_chunks");
    expect(payload).not.toContain("worker_trace");
  });

  it("keeps safe fallback when pipeline summary requires session", async () => {
    vi.mocked(fetchPipelineSummary).mockResolvedValue({
      ok: false,
      status: 401,
      source: "backend",
      error: {
        code: "unauthorized",
        message: "Sessão necessária."
      }
    });

    const viewModel = await loadPipelineDetail("material-arte-naval");

    expect(viewModel.connection.title).toBe("Requer sessão");
    expect(viewModel.detail?.source).toBe("mock");
  });

  it("returns friendly not-found state when pipeline summary is outside the session", async () => {
    vi.mocked(fetchPipelineSummary).mockResolvedValue({
      ok: false,
      status: 404,
      source: "backend",
      error: {
        code: "not_found",
        message: "Este conteúdo não está disponível nesta sessão."
      }
    });

    const viewModel = await loadPipelineDetail("doc-fora-da-sessao");

    expect(viewModel.connection.title).toBe("Item não encontrado");
    expect(viewModel.detail).toBeNull();
  });
});
