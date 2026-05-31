"use client";

import { useEffect, useState } from "react";

import { Card, CardTitle } from "@/components/ui/card";
import type { EditaisWorkspaceViewModel } from "@/lib/api/types";
import { buildMockEditaisWorkspaceViewModel, loadEditaisWorkspaceViewModel } from "@/lib/adapters/editais";
import {
  buildDefaultRealUserStudyReadiness,
  loadRealUserStudyReadiness,
  type RealUserStudyReadiness
} from "@/lib/adapters/real-user-state";
import {
  productStatusClass,
  WorkspaceLink,
  WorkspaceSummaryGrid
} from "@/components/workspace/WorkspaceShared";
import { Badge } from "@/components/ui/badge";
import type { EditalListItem } from "@/lib/api/types";

function isNotReadyEdital(item: EditalListItem): boolean {
  return item.analysisStatus === "not_ready" || item.analysisStatus === "uploaded_not_analyzed";
}

export function EditaisReadOnlyClient() {
  const [viewModel, setViewModel] = useState<EditaisWorkspaceViewModel>(buildMockEditaisWorkspaceViewModel());
  const [readiness, setReadiness] = useState<RealUserStudyReadiness>(buildDefaultRealUserStudyReadiness());

  useEffect(() => {
    let active = true;
    void Promise.all([loadEditaisWorkspaceViewModel(), loadRealUserStudyReadiness()]).then(
      ([nextViewModel, nextReadiness]) => {
        if (active) {
          setViewModel(nextViewModel);
          setReadiness(nextReadiness);
        }
      }
    );
    return () => {
      active = false;
    };
  }, []);

  const hasRealEditalItems =
    viewModel.connection.state === "connected" && viewModel.connection.source === "backend" && viewModel.items.length > 0;
  const hasAnalyzedEditalItems = hasRealEditalItems && viewModel.items.some((item) => !isNotReadyEdital(item));
  const showEmptyState = !hasRealEditalItems;
  const emptyStateTitle =
    readiness.editalAnalysisState === "analysis_unavailable"
      ? "Análise indisponível"
      : readiness.editalAnalysisState === "edital_uploaded_not_analyzed"
        ? "Edital enviado"
        : "Nenhum edital analisado ainda.";

  return (
    <div className="space-y-8">
      <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
        <div className="section-kicker">editais</div>
        <CardTitle className="mt-5 break-words text-[2rem] leading-[0.95] sm:text-[2.2rem]">
          Editais
        </CardTitle>
        <p className="mt-4 max-w-2xl text-sm leading-8 text-silver">
          Acompanhe quando houver edital analisado. Um arquivo classificado como edital aparece primeiro como enviado;
          a análise vem depois.
        </p>
      </Card>

      {hasAnalyzedEditalItems ? <WorkspaceSummaryGrid items={viewModel.summary} /> : null}

      {hasRealEditalItems ? (
        <section className="grid gap-4 lg:grid-cols-2">
          {viewModel.items.map((item) => {
            const notReady = isNotReadyEdital(item);

            return (
          <Card key={item.id} className="flex h-full min-w-0 flex-col">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0 max-w-[19rem]">
                <div className="section-kicker">edital</div>
                <CardTitle className="mt-4 break-words text-[1.55rem] leading-[1.02] sm:text-[1.8rem]">
                  {item.title}
                </CardTitle>
              </div>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <Badge className={productStatusClass(item.statusLabel)}>{item.statusLabel}</Badge>
              <Badge className={productStatusClass(item.reviewState)}>{item.reviewState}</Badge>
            </div>
            {notReady ? (
              <div className="mt-5 rounded-2xl border border-[rgba(201,169,110,0.16)] bg-[rgba(201,169,110,0.06)] p-4">
                <p className="text-sm leading-7 text-silver">
                  Este edital foi recebido, mas ainda não há tópicos ou bibliografia prontos para orientar o estudo.
                </p>
                <p className="mt-2 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
                  Confira se o arquivo tem texto extraível ou envie uma versão textual.
                </p>
              </div>
            ) : (
              <>
                <div className="mt-5 grid gap-3 sm:grid-cols-3">
                  <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
                    <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                      tópicos
                    </div>
                    <p className="mt-2 text-sm text-ink">{item.topicsCount}</p>
                  </div>
                  <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
                    <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                      bibliografia
                    </div>
                    <p className="mt-2 text-sm text-ink">{item.bibliographyItemsCount}</p>
                  </div>
                  <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
                    <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                      gaps
                    </div>
                    <p className="mt-2 text-sm text-ink">{item.gapsCount}</p>
                  </div>
                </div>
                <p className="mt-5 text-sm leading-7 text-silver">
                  O edital analisado ajuda a organizar tópicos, bibliografia e lacunas para conferência.
                </p>
              </>
            )}
            <div className="mt-6 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
              <span className="max-w-[18rem] text-xs uppercase tracking-[0.18em] text-[rgba(232,238,242,0.42)]">
                {notReady ? "Análise ainda não concluída." : "Análise sujeita a revisão."}
              </span>
              <WorkspaceLink href={`/editais/${item.id}`}>Ver edital</WorkspaceLink>
            </div>
          </Card>
            );
          })}
        </section>
      ) : (
        <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
          <div className="section-kicker">editais</div>
          <CardTitle className="mt-5 text-[1.8rem]">{emptyStateTitle}</CardTitle>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
            {readiness.editalAnalysisState === "analysis_unavailable"
              ? "Não foi possível carregar o estado do edital agora. Você pode tentar novamente ou voltar para materiais."
              : readiness.editalAnalysisState === "edital_uploaded_not_analyzed"
                ? "A análise do edital ainda não foi executada nesta versão."
              : readiness.isAuthenticated
                ? "Envie um arquivo classificado como edital para iniciar esse fluxo."
                : "Entre para ver seus editais analisados."}
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <WorkspaceLink href="/materials/upload">Enviar edital</WorkspaceLink>
            <WorkspaceLink href="/materials">Ver materiais</WorkspaceLink>
          </div>
        </Card>
      )}
    </div>
  );
}
