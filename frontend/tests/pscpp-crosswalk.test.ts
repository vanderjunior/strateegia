import { describe, expect, it } from "vitest";

import { buildMockPscppCrosswalkViewModel } from "@/lib/adapters/pscpp-crosswalk";

describe("PSCPP crosswalk adapter", () => {
  it("returns five priority blocks with coverage labels", () => {
    const viewModel = buildMockPscppCrosswalkViewModel();

    expect(viewModel.blocks).toHaveLength(5);
    expect(viewModel.blocks.every((block) => Boolean(block.coverageLabel))).toBe(true);
    expect(viewModel.blocks.every((block) => block.priorityNumber > 0)).toBe(true);
  });

  it("includes reinforcement guidance, read-only links, and suggested sessions", () => {
    const viewModel = buildMockPscppCrosswalkViewModel();

    expect(viewModel.mainGaps.every((gap) => Boolean(gap.suggestedAction))).toBe(true);
    expect(
      viewModel.relationships.every(
        (item) =>
          item.material.linkHref.startsWith("/materials/") &&
          item.edital.linkHref.startsWith("/editais/")
      )
    ).toBe(true);
    expect(
      viewModel.blocks.every(
        (block) =>
          block.suggestedSessions.length > 0 &&
          block.suggestedSessions.every((session) => session.label.startsWith("Sessão"))
      )
    ).toBe(true);
  });

  it("keeps the crosswalk guidance-only and free of generation or scheduling actions", () => {
    const viewModel = buildMockPscppCrosswalkViewModel();
    const serialized = JSON.stringify(viewModel);

    expect(serialized).not.toContain("Gerar questões");
    expect(serialized).not.toContain("Gerar simulado");
    expect(serialized).not.toContain("Aplicar progresso");
    expect(serialized).not.toContain("Agendar");
    expect(serialized).not.toContain("Começar sessão");
  });
});
