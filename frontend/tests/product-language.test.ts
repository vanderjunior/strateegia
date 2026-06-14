import { describe, expect, it } from "vitest";

import {
  getSafeProductCopy,
  getUserFacingCapability,
  getUserFacingStatus,
  shouldShowCapability,
  translateInternalTerm
} from "@/lib/product/product-language";

describe("product language helpers", () => {
  it("translates internal runtime terms for student-facing copy", () => {
    const translated = translateInternalTerm(
      "applied event ledger with propagation guardrail and controlled propagation apply",
      "student"
    );

    expect(translated).toContain("registro de aplicacao");
    expect(translated).toContain("protecao contra atualizacao indevida");
    expect(translated).toContain("atualizacao controlada");
    expect(translated).not.toContain("ledger");
    expect(translated).not.toContain("guardrail");
    expect(translated).not.toContain("propagation");
    expect(translated).not.toContain("artifact");
    expect(translated).not.toContain("runtime chain");
    expect(translated).not.toContain("mutation transaction");
  });

  it("preserves internal terms for developer-facing copy", () => {
    const translated = translateInternalTerm("applied event ledger", "developer");
    expect(translated).toBe("applied event ledger");
  });

  it("returns user-facing capability labels and safe statuses", () => {
    const progress = getUserFacingCapability("minimal_progress_ledger_apply", "student");
    const ocr = getUserFacingCapability("ocr_adapter", "student");
    const draft = getUserFacingCapability("question_draft_generation", "student");

    expect(progress?.label).toBe("Progresso registrado com segurança");
    expect(ocr?.label).toBe("PDF que exige conferência");
    expect(ocr?.safeStatusLabels).toContain("Precisa de conferência");
    expect(draft?.safeStatusLabels).toContain("Revisão necessária");
    expect(shouldShowCapability("runtime_apply_policy", "student")).toBe(true);
  });

  it("maps capability status enums to friendly labels", () => {
    expect(getUserFacingStatus("implemented_and_tested", "student")).toMatchObject({
      label: "Validado",
      tone: "positive"
    });
    expect(getUserFacingStatus("partially_implemented", "student")).toMatchObject({
      label: "Parcial",
      tone: "warning"
    });
    expect(getUserFacingStatus("foundation_only", "student")).toMatchObject({
      label: "Ainda não executável",
      tone: "neutral"
    });
    expect(getUserFacingStatus("not_implemented", "student")).toMatchObject({
      label: "Não implementado",
      tone: "muted"
    });
  });

  it("exposes product-safe copy labels for dashboard and workspaces", () => {
    expect(getSafeProductCopy("materialProcessed")).toBe("Material processado");
    expect(getSafeProductCopy("gapsFound")).toBe("Pontos a revisar");
    expect(getSafeProductCopy("notExecutableYet")).toBe("Ainda não executável");
  });
});
