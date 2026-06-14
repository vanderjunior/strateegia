import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  buildMockStudySessionDetail,
  buildMockStudySessionWorkspaceViewModel
} from "@/lib/adapters/study-sessions";
import { fetchNextStudySession } from "@/lib/api/study";

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

  it("keeps session 12 explicit about review-only assessment limits", () => {
    const detail = buildMockStudySessionDetail("session-12-simulado-curto-revisao");

    expect(detail).not.toBeNull();
    expect(detail?.cautions).toContain("Avaliação completa fica para depois.");
    expect(detail?.cautions).toContain("Questões de fixação ainda exigem revisão.");
    expect(detail?.cautions).toContain("Esta tela não cria prova nem corrige respostas.");
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

describe("next study session API helper", () => {
  const originalBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  const originalMockApi = process.env.NEXT_PUBLIC_USE_MOCK_API;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8000";
    process.env.NEXT_PUBLIC_USE_MOCK_API = "false";
    vi.unstubAllGlobals();
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = originalBaseUrl;
    process.env.NEXT_PUBLIC_USE_MOCK_API = originalMockApi;
    vi.unstubAllGlobals();
  });

  it("maps a ready next study session response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            session_status: "ready",
            session_id: "study-session:doc-1",
            document_id: "doc-1",
            material_title: "Aula preparada",
            material_type: "study_material",
            summary_status: "ready",
            estimated_minutes: 5,
            sections_count: 1,
            items: [
              {
                section_id: "section-1",
                title: "Atos administrativos",
                summary: "Resumo em preparação para esta seção.",
                key_points: ["Atos administrativos"],
                estimated_minutes: 5,
                status: "ready"
              }
            ],
            next_actions: [{ label: "Abrir material", href: "/materials/doc-1" }],
            message: "Comece por este material preparado.",
            source: "user_scope"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const result = await fetchNextStudySession();

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.data.session_status).toBe("ready");
      if (result.data.session_status === "ready" || result.data.session_status === "needs_review") {
        expect(result.data.document_id).toBe("doc-1");
        expect(result.data.items).toHaveLength(1);
      }
    }
  });

  it("maps not-ready, auth, offline, and invalid responses safely", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            session_status: "not_ready",
            message: "Envie e prepare um material de estudo para começar.",
            next_actions: [{ label: "Enviar material", href: "/materials/upload" }],
            source: "user_scope"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );
    const notReady = await fetchNextStudySession();
    expect(notReady.ok).toBe(true);
    if (notReady.ok) {
      expect(notReady.data.session_status).toBe("not_ready");
    }

    vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 401 })));
    const unauthorized = await fetchNextStudySession();
    expect(unauthorized.ok).toBe(false);
    if (!unauthorized.ok) {
      expect(unauthorized.error.code).toBe("auth_required");
    }

    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );
    const offline = await fetchNextStudySession();
    expect(offline.ok).toBe(false);
    if (!offline.ok) {
      expect(offline.error.code).toBe("backend_offline");
    }

    vi.stubGlobal("fetch", vi.fn(async () => new Response("{}", { status: 200 })));
    const invalid = await fetchNextStudySession();
    expect(invalid.ok).toBe(false);
    if (!invalid.ok) {
      expect(invalid.error.code).toBe("invalid_response");
    }
  });
});
