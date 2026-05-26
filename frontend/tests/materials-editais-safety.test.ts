import { describe, expect, it } from "vitest";

import { buildMockEditalDetail, buildMockEditaisWorkspaceViewModel } from "@/lib/adapters/editais";
import { buildMockMaterialDetail, buildMockMaterialsWorkspaceViewModel } from "@/lib/adapters/materials";
import { buildMockPipelineDetail } from "@/lib/adapters/pipeline";

describe("materials/editais/pipeline product safety", () => {
  it("keeps serialized workspace and detail data free of forbidden fields and local paths", () => {
    const payload = JSON.stringify({
      materials: buildMockMaterialsWorkspaceViewModel(),
      materialDetail: buildMockMaterialDetail("material-arte-naval"),
      editais: buildMockEditaisWorkspaceViewModel(),
      editalDetail: buildMockEditalDetail("edital-pscpp-referencia"),
      pipeline: buildMockPipelineDetail("material-roteiro-porto")
    });

    const forbiddenTokens = [
      ["correct", "answer"].join("_"),
      ["correct", "option"].join("_"),
      ["answer", "key"].join("_"),
      ["answer", "key", "value"].join("_"),
      ["final", "answer", "key"].join("_"),
      ["final", "answer", "key", "content"].join("_"),
      ["gaba", "rito"].join(""),
      ["gaba", "rito", "final"].join("_"),
      ["correct", "ness"].join(""),
      ["is", "correct"].join("_"),
      ["raw", "document", "body"].join(" "),
      ["raw", "OCR", "text", "dump"].join(" "),
      ["base", "64"].join(""),
      ["password", "hash"].join("_"),
      ["session", "token"].join(" "),
      ["private", "path"].join(" "),
      ["storage", "root"].join(" "),
      "/Users/",
      "C:\\"
    ];

    forbiddenTokens.forEach((token) => {
      expect(payload).not.toContain(token);
    });
  });
});
