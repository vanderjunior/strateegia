import { describe, expect, it } from "vitest";

import {
  buildMockStudySessionDetail,
  buildMockStudySessionWorkspaceViewModel
} from "@/lib/adapters/study-sessions";

describe("study session adapters", () => {
  it("returns a next suggested session with core guidance fields", () => {
    const viewModel = buildMockStudySessionWorkspaceViewModel();
    const nextSession = viewModel.sessions.find((item) => item.id === viewModel.nextSuggestedSessionId);

    expect(nextSession).toBeDefined();
    expect(nextSession?.title).toBeTruthy();
    expect(nextSession?.objective).toBeTruthy();
    expect(nextSession?.priorityBlockTitle).toBeTruthy();
    expect(nextSession?.relatedMaterialsCount).toBeGreaterThanOrEqual(0);
    expect(nextSession?.relatedGapsCount).toBeGreaterThanOrEqual(0);
  });

  it("keeps session 12 explicit about review-only simulado limits", () => {
    const detail = buildMockStudySessionDetail("session-12-simulado-curto-revisao");

    expect(detail).not.toBeNull();
    expect(detail?.cautions).toContain("Simulado curto ainda não executável.");
    expect(detail?.cautions).toContain("Questões candidatas ainda exigem revisão.");
    expect(detail?.cautions).toContain("Esta tela não gera prova nem corrige respostas.");
  });

  it("does not expose mutation actions in session workspace or detail copy", () => {
    const viewModel = buildMockStudySessionWorkspaceViewModel();
    const detail = buildMockStudySessionDetail("session-1-manobrabilidade-forcas");
    const serialized = JSON.stringify({ viewModel, detail });

    expect(serialized).not.toContain("Começar sessão");
    expect(serialized).not.toContain("Concluir sessão");
    expect(serialized).not.toContain("Marcar como feito");
    expect(serialized).not.toContain("Aplicar progresso");
    expect(serialized).not.toContain("Agendar");
    expect(serialized).not.toContain("Gerar questões");
    expect(serialized).not.toContain("Gerar simulado");
  });
});
