import { describe, expect, it } from "vitest";

import {
  buildMockStudySessionDetail,
  buildMockStudySessionWorkspaceViewModel
} from "@/lib/adapters/study-sessions";
import { buildMockPscppWorkspaceViewModel } from "@/lib/adapters/pscpp";
import {
  editalDetailsById,
  materialDetailsById,
  materialsWorkspaceItems,
  pscppCrosswalkViewModelMock,
  studySessionDetailsById,
  studySessionWorkspaceViewModelMock
} from "@/lib/mock/mentorium-demo-data";

function compact(value: unknown): string {
  return JSON.stringify(value);
}

describe("product safety data", () => {
  it("keeps frontend mock and view-model data free of sensitive payload fields", () => {
    const payload = compact({
      materialsWorkspaceItems,
      materialDetailsById,
      editalDetailsById,
      pscppCrosswalkViewModelMock,
      studySessionWorkspaceViewModelMock,
      studySessionDetailsById,
      builtWorkspace: buildMockStudySessionWorkspaceViewModel(),
      builtSession: buildMockStudySessionDetail("session-12-simulado-curto-revisao"),
      builtPscpp: buildMockPscppWorkspaceViewModel()
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
      ["storage", "root"].join(" ")
    ];

    forbiddenTokens.forEach((token) => {
      expect(payload).not.toContain(token);
    });
  });
});
