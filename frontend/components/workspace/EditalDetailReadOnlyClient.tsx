"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import type { BackendConnectionInfo, EditalDetail } from "@/lib/api/types";
import { buildMockEditalDetail, loadEditalDetail } from "@/lib/adapters/editais";
import { sourceLabel } from "@/lib/adapters/capabilities";
import {
  productStatusClass,
  sourceBadgeClass,
  WorkspaceBackLink,
  WorkspaceSourcePanel
} from "@/components/workspace/WorkspaceShared";

function buildFallback(editalId: string): { connection: BackendConnectionInfo; detail: EditalDetail } {
  return {
    connection: {
      state: "mock",
      source: "mock",
      title: "Dados de demonstração",
      detail: "Demonstração exibida até existir leitura segura para este edital."
    },
    detail: buildMockEditalDetail(editalId) ?? {
      id: editalId,
      title: "Item não encontrado",
      statusLabel: "Análise candidata",
      topicsCount: 0,
      bibliographyItemsCount: 0,
      gapsCount: 0,
      reviewState: "Revisão necessária",
      source: "mock",
      topicCandidates: [],
      bibliographyCandidates: [],
      coverageItems: [],
      gapItems: [],
      warnings: ["Este conteúdo não está disponível nesta sessão."],
      notes: ["Consulte os dados de demonstração ou volte para a listagem de editais."]
    }
  };
}

export function EditalDetailReadOnlyClient({ editalId }: { editalId: string }) {
  const [viewModel, setViewModel] = useState<{ connection: BackendConnectionInfo; detail: EditalDetail | null }>(
    buildFallback(editalId)
  );

  useEffect(() => {
    let active = true;
    void loadEditalDetail(editalId).then((next) => {
      if (active) {
        setViewModel(next);
      }
    });
    return () => {
      active = false;
    };
  }, [editalId]);

  const { connection, detail } = viewModel;

  if (!detail) {
    return (
      <div className="space-y-8">
        <WorkspaceBackLink href="/editais">Voltar para editais</WorkspaceBackLink>

        <WorkspaceSourcePanel
          eyebrow="edital"
          title="Item não encontrado"
          subtitle="Este conteúdo não está disponível nesta sessão. Consulte os dados de demonstração ou volte para editais."
          connection={connection}
        />

        <Card className="min-w-0 border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.02)]">
          <CardTitle className="text-[1.8rem] leading-[1.04]">Consulte os editais disponíveis</CardTitle>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
            Entre para consultar detalhes reais deste edital. Enquanto isso, exemplos podem aparecer como apoio.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <WorkspaceBackLink href="/editais">Voltar para editais</WorkspaceBackLink>
          </div>
        </Card>
      </div>
    );
  }

  const isNotReady = detail.analysisStatus === "not_ready" || detail.analysisStatus === "uploaded_not_analyzed";

  return (
    <div className="space-y-8">
      <WorkspaceBackLink href="/editais">Voltar para editais</WorkspaceBackLink>

      <WorkspaceSourcePanel
        eyebrow="edital"
        title={detail.title}
        subtitle={
          isNotReady
            ? "Este edital foi recebido, mas a análise ainda não está concluída."
            : "Informações do edital organizadas para conferência."
        }
        connection={connection}
      />

      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="min-w-0">
          <div className="flex flex-wrap gap-2">
            <Badge className={sourceBadgeClass(detail.source)}>{sourceLabel(detail.source)}</Badge>
            <Badge className={productStatusClass(detail.statusLabel)}>{detail.statusLabel}</Badge>
            <Badge className={productStatusClass(detail.reviewState)}>{detail.reviewState}</Badge>
          </div>
          {isNotReady ? (
            <div className="mt-6 rounded-2xl border border-[rgba(201,169,110,0.16)] bg-[rgba(201,169,110,0.06)] p-4">
              <p className="text-sm leading-7 text-silver">
                Este edital foi recebido, mas ainda não há tópicos ou bibliografia prontos para orientar o estudo.
              </p>
              <p className="mt-2 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
                Confira se o arquivo tem texto extraível ou envie uma versão textual.
              </p>
            </div>
          ) : (
            <>
              <div className="mt-6 grid gap-4 md:grid-cols-3">
                <div>
                  <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                    tópicos
                  </div>
                  <p className="mt-2 text-sm text-ink">{detail.topicsCount}</p>
                </div>
                <div>
                  <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                    bibliografia
                  </div>
                  <p className="mt-2 text-sm text-ink">{detail.bibliographyItemsCount}</p>
                </div>
                <div>
                  <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                    gaps
                  </div>
                  <p className="mt-2 text-sm text-ink">{detail.gapsCount}</p>
                </div>
              </div>
              <p className="mt-6 text-sm leading-7 text-silver">
                Os itens abaixo são candidatos e permanecem sujeitos a revisão antes de qualquer uso posterior.
              </p>
            </>
          )}
        </Card>

        <Card className="min-w-0">
          <div className="section-kicker">avisos</div>
          <CardTitle className="mt-5 break-words text-[1.8rem]">Revisão necessária</CardTitle>
          <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
            {detail.warnings.map((warning) => (
              <li key={warning}>• {warning}</li>
            ))}
          </ul>
        </Card>
      </section>

      {isNotReady ? null : <section className="grid gap-4 xl:grid-cols-2">
        <Card className="min-w-0">
          <div className="section-kicker">tópicos candidatos</div>
          <CardTitle className="mt-5 break-words text-[1.8rem]">Tópicos candidatos</CardTitle>
          {detail.topicCandidates.length ? (
            <div className="mt-5 flex flex-wrap gap-2">
              {detail.topicCandidates.map((topic) => (
                <Badge
                  key={topic}
                  className="border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.08)] text-silver"
                >
                  {topic}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="mt-5 text-sm leading-7 text-silver">Nenhum tópico candidato para exibir ainda.</p>
          )}
        </Card>

        <Card className="min-w-0">
          <div className="section-kicker">bibliografia candidata</div>
          <CardTitle className="mt-5 break-words text-[1.8rem]">Bibliografia identificada</CardTitle>
          {detail.bibliographyCandidates.length ? (
            <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
              {detail.bibliographyCandidates.map((item) => (
                <li key={item} className="break-words">
                  • {item}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-5 text-sm leading-7 text-silver">Nenhuma referência para exibir ainda.</p>
          )}
        </Card>
      </section>}

      {isNotReady ? null : <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="min-w-0">
          <div className="section-kicker">cobertura</div>
          <CardTitle className="mt-5 break-words text-[1.8rem]">Alinhamento preliminar</CardTitle>
          <div className="mt-5 space-y-3">
            {detail.coverageItems.map((item) => (
              <div
                key={item.id}
                className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="break-words text-sm text-ink">{item.title}</p>
                  <Badge className={productStatusClass(item.coverageLabel)}>{item.coverageLabel}</Badge>
                </div>
                <p className="mt-3 text-sm leading-7 text-silver">{item.detail}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card className="min-w-0">
          <div className="section-kicker">gaps</div>
          <CardTitle className="mt-5 break-words text-[1.8rem]">Gaps encontrados</CardTitle>
          <div className="mt-5 space-y-3">
            {detail.gapItems.map((item) => (
              <div
                key={item.id}
                className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="break-words text-sm text-ink">{item.title}</p>
                  <Badge className={productStatusClass(item.severityLabel)}>{item.severityLabel}</Badge>
                </div>
                <p className="mt-3 text-sm leading-7 text-silver">{item.detail}</p>
              </div>
            ))}
          </div>
        </Card>
      </section>}

      <Card className="min-w-0">
        <div className="section-kicker">notas</div>
        <CardTitle className="mt-5 break-words text-[1.8rem]">
          {isNotReady ? "Análise ainda não concluída" : "Leitura sujeita a revisão"}
        </CardTitle>
        <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
          {detail.notes.map((note) => (
            <li key={note}>• {note}</li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
