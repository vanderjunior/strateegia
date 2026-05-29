"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import type { BackendConnectionInfo, StudySessionDetail } from "@/lib/api/types";
import {
  buildMockStudySessionDetail,
  loadStudySessionDetail,
  loadStudySessionWorkspaceViewModel
} from "@/lib/adapters/study-sessions";
import {
  productStatusClass,
  WorkspaceBackLink,
  WorkspaceLink,
  WorkspaceSourcePanel
} from "@/components/workspace/WorkspaceShared";
import { sourceLabel } from "@/lib/adapters/capabilities";
import { StudySessionMetaRow } from "@/components/workspace/StudySessionShared";

function buildFallback(sessionId: string): { connection: BackendConnectionInfo; detail: StudySessionDetail | null } {
  return {
    connection: {
      state: "mock",
      source: "mock",
      title: "Dados de demonstração",
      detail: "Sessão exibida por consulta local auditada enquanto a leitura do perfil PSCPP no backend não é necessária para este detalhe."
    },
    detail: buildMockStudySessionDetail(sessionId)
  };
}

function safeOutputLabel(label: string): string {
  const normalized = label.toLowerCase();
  if (normalized.includes("quest")) {
    return "Questões candidatas ainda não geradas";
  }
  if (normalized.includes("flashcard")) {
    return "Ideias de revisão para anotar";
  }
  if (normalized.includes("simulado")) {
    return "Pontos para revisar antes de simulado futuro";
  }
  return label;
}

export function StudySessionDetailClient({ sessionId }: { sessionId: string }) {
  const [viewModel, setViewModel] = useState<{ connection: BackendConnectionInfo; detail: StudySessionDetail | null }>(
    buildFallback(sessionId)
  );

  useEffect(() => {
    let active = true;
    void Promise.all([
      loadStudySessionWorkspaceViewModel(),
      loadStudySessionDetail(sessionId)
    ]).then(([workspace, detail]) => {
      if (active && detail) {
        setViewModel({
          connection: workspace.connection,
          detail
        });
      }
    });
    return () => {
      active = false;
    };
  }, [sessionId]);

  const { connection, detail } = viewModel;
  const usesDemoMaterials = connection.source === "mock";
  const isDemoGuidance = connection.source !== "backend";

  if (!detail) {
    return (
      <div className="space-y-8">
        <WorkspaceBackLink href="/study">Voltar para estudo</WorkspaceBackLink>

        <WorkspaceSourcePanel
          eyebrow="estudo / sessão"
          title="Item não encontrado"
          subtitle="Este conteúdo não está disponível nesta sessão. O guia segue acessível na área de estudo."
          connection={connection}
        />

        <Card className="border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.02)]">
          <CardTitle className="text-[1.8rem] leading-[1.04]">Escolha outra sessão sugerida</CardTitle>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
            Este conteúdo não está disponível nesta sessão. Consulte os dados de demonstração ou use a área de estudo
            para retomar a trilha sugerida sem alterar seu progresso.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <WorkspaceLink href="/study">Ver estudo de hoje</WorkspaceLink>
            <WorkspaceLink href="/pscpp/mapa">Ver mapa PSCPP</WorkspaceLink>
            <WorkspaceLink href="/pscpp/ciclo">Ver ciclo PSCPP</WorkspaceLink>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <WorkspaceBackLink href="/study">Voltar para estudo</WorkspaceBackLink>

      <WorkspaceSourcePanel
        eyebrow="estudo / sessão"
        title={detail.title}
        subtitle="Orientação de consulta com materiais, gaps e pontos de revisão, sem alterar seu progresso."
        connection={connection}
      />

      {isDemoGuidance ? (
        <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(201,169,110,0.06)]">
          <div className="section-kicker">exemplo de orientação</div>
          <CardTitle className="mt-5 text-[1.75rem] leading-[1.04]">
            Exemplo de orientação. Ainda não baseado no seu edital.
          </CardTitle>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
            Use esta tela para entender o formato do guia. Um caminho real depende de edital analisado e materiais da
            sua sessão.
          </p>
        </Card>
      ) : null}

      <section className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="h-full min-w-0">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 max-w-3xl flex-1">
              <div className="section-kicker">objetivo</div>
              <CardTitle className="mt-5 break-words text-[1.9rem] leading-[1.02]">Orientação sugerida</CardTitle>
              <p className="mt-4 text-sm leading-7 text-silver">{detail.objective}</p>
            </div>
            <Badge className={productStatusClass(detail.statusLabel)}>{detail.statusLabel}</Badge>
          </div>
          <div className="mt-5">
            <StudySessionMetaRow
              durationLabel={detail.durationLabel}
              relatedMaterialsCount={detail.relatedMaterialsCount}
              relatedGapsCount={detail.relatedGapsCount}
              statusLabel={detail.statusLabel}
            />
          </div>
          <p className="mt-5 text-sm leading-7 text-[rgba(232,238,242,0.68)]">{detail.priorityBlockTitle}</p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Badge className="border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.08)] text-silver">
              {sourceLabel(connection.source)}
            </Badge>
            <Badge className={productStatusClass("Guia flexível")}>Guia flexível</Badge>
            <Badge className={productStatusClass("Não altera seu progresso")}>Não altera seu progresso</Badge>
          </div>
        </Card>

        <Card className="h-full min-w-0">
          <div className="section-kicker">estrutura</div>
          <CardTitle className="mt-5 break-words text-[1.9rem] leading-[1.02]">Estrutura da orientação</CardTitle>
          <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
            {detail.structure.map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ul>
          <div className="mt-6 flex flex-wrap gap-3">
            <WorkspaceLink href="/pscpp/mapa">Ver mapa PSCPP</WorkspaceLink>
            <WorkspaceLink href="/pscpp/ciclo">Ver ciclo PSCPP</WorkspaceLink>
          </div>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <Card className="h-full min-w-0">
          <div className="section-kicker">materiais e edital</div>
          <CardTitle className="mt-5 break-words text-[1.9rem] leading-[1.02]">Materiais relacionados</CardTitle>
          <div className="mt-5 space-y-3">
            {detail.relatedMaterials.length ? (
              detail.relatedMaterials.map((material) => (
                <div
                  key={material.id}
                  className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="break-words text-sm text-ink">{material.title}</p>
                      <p className="mt-2 text-sm leading-7 text-silver">{material.typeLabel}</p>
                    </div>
                    <Badge className={productStatusClass(material.statusLabel)}>{material.statusLabel}</Badge>
                  </div>
                  <div className="mt-4">
                    <Link
                      href={usesDemoMaterials ? "/materials" : material.linkHref}
                      className="inline-flex items-center justify-center rounded-xl border border-[rgba(168,184,196,0.12)] bg-transparent px-4 py-2 text-sm text-silver transition hover:border-[rgba(201,169,110,0.24)] hover:text-ink"
                    >
                      {usesDemoMaterials ? "Exemplo de material" : "Ver material"}
                    </Link>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm leading-7 text-silver">Nenhum material relacionado com cobertura suficiente ainda.</p>
            )}
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            {detail.relatedEditais.map((edital) => (
              <WorkspaceLink key={edital.id} href={edital.linkHref}>
                Ver edital
              </WorkspaceLink>
            ))}
          </div>
        </Card>

        <Card className="h-full min-w-0">
          <div className="section-kicker">gaps conectados</div>
          <CardTitle className="mt-5 break-words text-[1.9rem] leading-[1.02]">Checklist de estudo</CardTitle>
          <div className="mt-5 space-y-3">
            {detail.relatedGaps.map((gap) => (
              <div
                key={gap.id}
                className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
              >
                <p className="break-words text-sm text-ink">{gap.title}</p>
                <p className="mt-2 text-sm leading-7 text-silver">{gap.detail}</p>
              </div>
            ))}
          </div>
          <ul className="mt-6 space-y-3 text-sm leading-7 text-silver">
            {detail.checklist.map((item) => (
              <li key={item.id}>• {item.label}</li>
            ))}
          </ul>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="h-full min-w-0">
          <div className="section-kicker">ideias de revisão</div>
          <CardTitle className="mt-5 break-words text-[1.9rem] leading-[1.02]">Pontos para anotar</CardTitle>
          <div className="mt-5 space-y-3">
            {detail.outputs.map((output) => (
              <div
                key={output.id}
                className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <p className="min-w-0 flex-1 break-words text-sm text-ink">{safeOutputLabel(output.label)}</p>
                  <Badge className={productStatusClass(output.statusLabel)}>{output.statusLabel}</Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="h-full min-w-0">
          <div className="section-kicker">cautelas</div>
          <CardTitle className="mt-5 break-words text-[1.9rem] leading-[1.02]">Limites desta tela</CardTitle>
          <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
            {detail.cautions.map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ul>
          <div className="mt-6 flex flex-wrap gap-3">
            <WorkspaceLink href="/materials">Ver materiais</WorkspaceLink>
            <WorkspaceLink href="/pscpp/questoes">Ver questões PSCPP</WorkspaceLink>
          </div>
        </Card>
      </section>
    </div>
  );
}
