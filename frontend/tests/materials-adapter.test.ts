import { describe, expect, it } from "vitest";

import {
  buildMockMaterialDetail,
  buildMockMaterialsWorkspaceViewModel
} from "@/lib/adapters/materials";

describe("materials adapter", () => {
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
    const payload = JSON.stringify({ scanned, textual });

    expect(scanned.warnings.some((warning) => warning.includes("OCR"))).toBe(true);
    expect(scanned.sectionPreviews.every((section) => Boolean(section.title))).toBe(true);
    expect(textual.sectionPreviews.every((section) => Boolean(section.chunkRangeLabel))).toBe(true);

    expect(payload).not.toContain(["raw", "document", "body"].join(" "));
    expect(payload).not.toContain(["raw", "OCR", "text", "dump"].join(" "));
    expect(payload).not.toContain(["base", "64"].join(""));
    expect(payload).not.toContain("/Users/");
    expect(payload).not.toContain(["gaba", "rito"].join(""));
  });
});
