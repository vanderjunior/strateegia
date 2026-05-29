"use client";

import { useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { StudySessionMetaRow } from "@/components/workspace/StudySessionShared";
import {
  productStatusClass,
  WorkspaceLink,
  sourceBadgeClass
} from "@/components/workspace/WorkspaceShared";
import type { StudySessionWorkspaceViewModel } from "@/lib/api/types";
import {
  buildMockStudySessionWorkspaceViewModel,
  loadStudySessionWorkspaceViewModel
} from "@/lib/adapters/study-sessions";
import { sourceLabel } from "@/lib/adapters/capabilities";

export function DashboardStudyBridge() {
  const [viewModel, setViewModel] = useState<StudySessionWorkspaceViewModel>(
    buildMockStudySessionWorkspaceViewModel()
  );

  useEffect(() => {
    let active = true;

    void loadStudySessionWorkspaceViewModel().then((next) => {
      if (active) {
        setViewModel(next);
      }
    });

    return () => {
      active = false;
    };
  }, []);

  const nextSession = useMemo(
    () => viewModel.sessions.find((item) => item.id === viewModel.nextSuggestedSessionId) ?? viewModel.sessions[0],
    [viewModel]
  );

  return (
    <section className="overflow-hidden rounded-[32px] border border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)] p-6 lg:p-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 max-w-3xl">
          <div className="section-kicker">orientação de estudo</div>
          <CardTitle className="mt-5 break-words text-[2rem] leading-[0.98] sm:text-[2.2rem]">
            Orientação de estudo
          </CardTitle>
          <p className="mt-4 max-w-2xl text-sm leading-8 text-silver">
            Abra uma orientação de estudo quando o edital e os materiais reais estiverem conectados.
          </p>
        </div>
        <div className="flex max-w-full flex-wrap gap-2 lg:justify-end">
          <Badge className={sourceBadgeClass(viewModel.connection.source)}>{sourceLabel(viewModel.connection.source)}</Badge>
          <Badge className={productStatusClass("Guia flexível")}>Guia flexível</Badge>
          <Badge className={productStatusClass("Não altera seu progresso")}>Não altera seu progresso</Badge>
        </div>
      </div>

      {nextSession ? (
        <div className="mt-6 grid gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,0.85fr)]">
          <Card className="h-full min-w-0 border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.03)]">
            <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-silver">
              Sessão sugerida
            </div>
            <CardTitle className="mt-5 break-words text-[1.8rem] leading-[1.02] sm:text-[1.95rem]">
              {nextSession.title}
            </CardTitle>
            <p className="mt-4 text-sm leading-7 text-silver">{nextSession.objective}</p>
            <div className="mt-4 rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                bloco prioritário
              </div>
              <p className="mt-2 break-words text-sm leading-7 text-[rgba(232,238,242,0.72)]">
                {nextSession.priorityBlockTitle}
              </p>
            </div>
            <div className="mt-5">
              <StudySessionMetaRow
                durationLabel={nextSession.durationLabel}
                relatedMaterialsCount={nextSession.relatedMaterialsCount}
                relatedGapsCount={nextSession.relatedGapsCount}
                statusLabel={nextSession.statusLabel}
              />
            </div>
            <p className="mt-5 text-sm leading-7 text-silver">
              Questões candidatas em revisão. Esta ponte não cria agenda, não altera progresso e não
              executa simulado.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <WorkspaceLink href={`/study/session/${nextSession.id}`}>Abrir orientação</WorkspaceLink>
              <WorkspaceLink href="/study">Ver estudo</WorkspaceLink>
            </div>
          </Card>

          <Card className="h-full min-w-0 border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.03)]">
            <div className="section-kicker">atalhos de consulta</div>
            <CardTitle className="mt-5 text-[1.7rem] leading-[1.04]">Próximos passos de leitura</CardTitle>
            <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
              <li>Revise o mapa PSCPP para entender cobertura, gaps e prioridade do bloco atual.</li>
              <li>Use o ciclo PSCPP como sugestão flexível, sem criar agenda automaticamente.</li>
              <li>Abra os materiais relacionados antes de revisar questões candidatas.</li>
            </ul>
            <p className="mt-5 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
              Guia flexível, sem agenda, sem progresso automático e sem geração de questões ou simulado.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <WorkspaceLink href="/pscpp/mapa">Ver mapa PSCPP</WorkspaceLink>
              <WorkspaceLink href="/pscpp/ciclo">Ver ciclo PSCPP</WorkspaceLink>
              <WorkspaceLink href="/materials">Ver materiais</WorkspaceLink>
            </div>
          </Card>
        </div>
      ) : (
        <div className="mt-6">
          <Card className="min-w-0 border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.03)]">
            <CardTitle className="text-[1.7rem] leading-[1.05]">Nenhuma sessão sugerida para exibir agora</CardTitle>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
              Consulte o ciclo PSCPP para revisar o caminho de estudo.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <WorkspaceLink href="/pscpp/ciclo">Ver ciclo PSCPP</WorkspaceLink>
            </div>
          </Card>
        </div>
      )}
    </section>
  );
}
