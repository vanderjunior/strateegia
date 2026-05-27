import { describe, expect, it } from "vitest";

import { buildMockPipelineDetail } from "@/lib/adapters/pipeline";

describe("pipeline adapter", () => {
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
});
