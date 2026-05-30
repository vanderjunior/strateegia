import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/config", () => ({
  getApiConfig: vi.fn()
}));

import { uploadMaterialFile } from "@/lib/api/documents";
import { getApiConfig } from "@/lib/api/config";

function makeFile() {
  return new File(["demo"], "material.pdf", { type: "application/pdf" });
}

describe("upload error classification", () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: false
    });
  });

  it("returns mock mode without calling fetch", async () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: "http://127.0.0.1:8000",
      forceMock: true
    });
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const result = await uploadMaterialFile(makeFile());

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("mock_mode");
    expect(result.error.message).toBe("Modo de demonstração: nenhum arquivo foi enviado.");
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("returns api_base_missing when backend URL is absent", async () => {
    vi.mocked(getApiConfig).mockReturnValue({
      baseUrl: null,
      forceMock: false
    });

    const result = await uploadMaterialFile(makeFile());

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("api_base_missing");
    expect(result.error.message).toBe("Envio real não configurado.");
  });

  it.each([
    [401, "auth_required", "Sessão necessária para enviar material."],
    [403, "auth_required", "Sessão necessária para enviar material."],
    [404, "endpoint_unavailable", "Endpoint de envio indisponível neste ambiente."],
    [405, "method_not_allowed", "Endpoint encontrado, mas o método de envio não foi aceito."],
    [413, "file_too_large", "O arquivo excede o limite atual de 5 MB."],
    [415, "unsupported_file_type", "Tipo de arquivo não aceito."],
    [400, "validation_failed", "Arquivo não pôde ser validado."],
    [422, "validation_failed", "Arquivo não pôde ser validado."],
    [502, "backend_offline", "Não foi possível carregar os dados agora."]
  ])("maps HTTP %i to %s", async (status, code, message) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("{}", { status, headers: { "content-type": "application/json" } }))
    );

    const result = await uploadMaterialFile(makeFile());

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe(code);
    expect(result.error.message).toBe(message);
  });

  it("treats thrown fetch failures as backend_offline", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("fetch failed");
      })
    );

    const result = await uploadMaterialFile(makeFile());

    expect(result.ok).toBe(false);
    if (result.ok) {
      throw new Error("expected failure");
    }
    expect(result.error.code).toBe("backend_offline");
    expect(result.error.message).toBe("Não foi possível carregar os dados agora.");
  });

  it("sends material_type and preserves requested type when upload response is sparse", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(
        JSON.stringify({
          metadata: {
            document_id: "doc-edital",
            filename: "edital.md",
            original_filename: "edital.md",
            content_type: "text/markdown",
            size_bytes: 12,
            status: "extracted",
            extraction_status: "extracted"
          }
        }),
        { status: 201, headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchSpy);

    const result = await uploadMaterialFile(new File(["conteudo"], "edital.md", { type: "text/markdown" }), "edital");
    const fetchCalls = (fetchSpy as unknown as { mock: { calls: [string, RequestInit][] } }).mock.calls;
    const formData = fetchCalls[0][1].body as FormData;

    expect(formData.get("material_type")).toBe("edital");
    expect(result.ok).toBe(true);
    if (!result.ok) {
      throw new Error("expected success");
    }
    expect(result.data.materialType).toBe("edital");
    expect(result.data.materialTypeLabel).toBe("Edital");
  });
});
