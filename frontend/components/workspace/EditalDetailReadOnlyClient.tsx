"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import type { BackendConnectionInfo, EditalDetail } from "@/lib/api/types";
import { buildMockEditalDetail, loadEditalDetail } from "@/lib/adapters/editais";
import { sourceLabel } from "@/lib/adapters/capabilities";
import { productStatusClass, sourceBadgeClass, WorkspaceSourcePanel } from "@/components/workspace/WorkspaceShared";

function buildFallback(editalId: string): { connection: BackendConnectionInfo; detail: EditalDetail } {
  return {
    connection: {
      state: "mock",
      source: "mock",
      title: "Usando dados de demonstração",
      detail: "Detalhes locais exibidos até existir leitura segura do backend para este edital."
    },
    detail: buildMockEditalDetail(editalId)
  };
}

export function EditalDetailReadOnlyClient({ editalId }: { editalId: string }) {
  const [viewModel, setViewModel] = useState<{ connection: BackendConnectionInfo; detail: EditalDetail }>(
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

  return (
    <div className="space-y-8">
      <WorkspaceSourcePanel
        eyebrow="edital"
        title={detail.title}
        subtitle="Tópicos, bibliografia e alinhamento preliminar mostrados em linguagem de produto e sujeitos a revisão."
        connection={connection}
      />

      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <div className="flex flex-wrap gap-2">
            <Badge className={sourceBadgeClass(detail.source)}>{sourceLabel(detail.source)}</Badge>
            <Badge className={productStatusClass(detail.statusLabel)}>{detail.statusLabel}</Badge>
            <Badge className={productStatusClass(detail.reviewState)}>{detail.reviewState}</Badge>
          </div>
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
        </Card>

        <Card>
          <div className="section-kicker">avisos</div>
          <CardTitle className="mt-5 text-[1.8rem]">Conferência humana</CardTitle>
          <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
            {detail.warnings.map((warning) => (
              <li key={warning}>• {warning}</li>
            ))}
          </ul>
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <Card>
          <div className="section-kicker">tópicos candidatos</div>
          <CardTitle className="mt-5 text-[1.8rem]">Tópicos identificados</CardTitle>
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

        <Card>
          <div className="section-kicker">bibliografia candidata</div>
          <CardTitle className="mt-5 text-[1.8rem]">Referências identificadas</CardTitle>
          {detail.bibliographyCandidates.length ? (
            <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
              {detail.bibliographyCandidates.map((item) => (
                <li key={item}>• {item}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-5 text-sm leading-7 text-silver">Nenhuma referência para exibir ainda.</p>
          )}
        </Card>
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <div className="section-kicker">cobertura</div>
          <CardTitle className="mt-5 text-[1.8rem]">Alinhamento preliminar</CardTitle>
          <div className="mt-5 space-y-3">
            {detail.coverageItems.map((item) => (
              <div
                key={item.id}
                className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm text-ink">{item.title}</p>
                  <Badge className={productStatusClass(item.coverageLabel)}>{item.coverageLabel}</Badge>
                </div>
                <p className="mt-3 text-sm leading-7 text-silver">{item.detail}</p>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <div className="section-kicker">gaps</div>
          <CardTitle className="mt-5 text-[1.8rem]">Lacunas identificadas</CardTitle>
          <div className="mt-5 space-y-3">
            {detail.gapItems.map((item) => (
              <div
                key={item.id}
                className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm text-ink">{item.title}</p>
                  <Badge className={productStatusClass(item.severityLabel)}>{item.severityLabel}</Badge>
                </div>
                <p className="mt-3 text-sm leading-7 text-silver">{item.detail}</p>
              </div>
            ))}
          </div>
        </Card>
      </section>

      <Card>
        <div className="section-kicker">notas</div>
        <CardTitle className="mt-5 text-[1.8rem]">Leitura sujeita a revisão</CardTitle>
        <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
          {detail.notes.map((note) => (
            <li key={note}>• {note}</li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
