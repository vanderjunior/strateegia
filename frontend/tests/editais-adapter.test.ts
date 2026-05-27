import { describe, expect, it } from "vitest";

import {
  buildMockEditalDetail,
  buildMockEditaisWorkspaceViewModel
} from "@/lib/adapters/editais";

describe("editais adapter", () => {
  it("returns a mock-first edital overview with cautious product language", () => {
    const viewModel = buildMockEditaisWorkspaceViewModel();
    const edital = viewModel.items.find((item) => item.id === "edital-pscpp-referencia");

    expect(edital).toBeDefined();
    expect(edital?.title).toContain("PSCPP/Praticagem");
    expect(edital?.topicsCount).toBeGreaterThanOrEqual(0);
    expect(edital?.bibliographyItemsCount).toBeGreaterThanOrEqual(0);
    expect(edital?.gapsCount).toBeGreaterThanOrEqual(0);
    expect(edital?.statusLabel).toBe("Análise candidata");
    expect(edital?.reviewState).toBe("Precisa de conferência");
  });

  it("returns detail with candidates, coverage labels, and non-final wording", () => {
    const detail = buildMockEditalDetail("edital-pscpp-referencia");
    expect(detail).not.toBeNull();
    const serialized = JSON.stringify(detail);

    expect(detail?.topicCandidates.length).toBeGreaterThan(0);
    expect(detail?.bibliographyCandidates.length).toBeGreaterThan(0);
    expect(detail?.gapItems.length).toBeGreaterThan(0);
    expect(detail?.coverageItems.map((item) => item.coverageLabel)).toEqual(
      expect.arrayContaining(["Cobertura boa", "Cobertura parcial", "Gap encontrado", "Precisa de material"])
    );
    expect(detail?.notes).toEqual(
      expect.arrayContaining([
        expect.stringContaining("Alinhamento preliminar"),
        expect.stringContaining("revisão")
      ])
    );

    expect(serialized).toContain("verdade final");
    expect(serialized).not.toContain(["raw", "document", "body"].join(" "));
    expect(serialized).not.toContain(["gaba", "rito"].join(""));
  });

  it("returns null for an unknown edital detail id", () => {
    expect(buildMockEditalDetail("edital-desconhecido")).toBeNull();
  });
});
