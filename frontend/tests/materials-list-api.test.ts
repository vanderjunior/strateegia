import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

import { fetchUserMaterialsList } from "@/lib/api/documents";
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
    [502, "backend_offline", "Não foi possível conectar ao backend."],
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
                content_type: "application/pdf",
                status: "metadata_ready",
                uploaded_at: "2026-05-27T00:00:00Z",
                extraction_status: "extracted",
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
    expect(JSON.stringify(result.data)).not.toContain("token");
    expect(JSON.stringify(result.data)).not.toContain("cookie");
  });
});
