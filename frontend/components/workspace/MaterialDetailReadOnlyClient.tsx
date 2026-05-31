"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { analyzeMaterialAsEdital } from "@/lib/api/editais";
import { prepareStudyMaterial } from "@/lib/api/documents";
import type {
  ApiResult,
  BackendConnectionInfo,
  BackendEditalAnalysisResponse,
  BackendStudyMaterialPreparationResponse,
  MaterialDetail
} from "@/lib/api/types";
import { buildMockMaterialDetail, loadMaterialDetail } from "@/lib/adapters/materials";
import { sourceLabel } from "@/lib/adapters/capabilities";
import {
  productStatusClass,
  sourceBadgeClass,
  WorkspaceBackLink,
  WorkspaceLink,
  WorkspaceSourcePanel
} from "@/components/workspace/WorkspaceShared";

function buildFallback(materialId: string): { connection: BackendConnectionInfo; detail: MaterialDetail } {
  return {
    connection: {
      state: "mock",
      source: "mock",
      title: "Dados de demonstração",
      detail: "Demonstração exibida até existir leitura segura para este material."
    },
    detail: buildMockMaterialDetail(materialId) ?? {
      id: materialId,
      title: "Item não encontrado",
      typeLabel: "Material",
      materialType: "unknown",
      materialTypeLabel: "Tipo não informado",
      processingStatus: "Revisão necessária",
      extractionStatus: "Demonstração",
      sectionsCount: null,
      chunksCount: null,
      reviewState: "Revisão necessária",
      source: "mock",
      relatedGaps: 0,
      warnings: ["Este conteúdo não está disponível nesta sessão."],
      sectionPreviews: [],
      sourceNote: "Consulte os dados de demonstração ou volte para a listagem de materiais."
    }
  };
}

type EditalAnalysisUiState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "analyzed"; data: BackendEditalAnalysisResponse }
  | { status: "needs_review"; data: BackendEditalAnalysisResponse }
  | { status: "not_ready" }
  | { status: "invalid_material_type" }
  | { status: "not_found" }
  | { status: "offline" }
  | { status: "unauthorized" };

type StudyPreparationUiState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready_for_study"; data: BackendStudyMaterialPreparationResponse }
  | { status: "needs_review"; data: BackendStudyMaterialPreparationResponse }
  | { status: "not_ready" }
  | { status: "invalid_material_type" }
  | { status: "not_found" }
  | { status: "offline" }
  | { status: "unauthorized" };

function editalAnalysisStateFromResult(result: ApiResult<BackendEditalAnalysisResponse>): EditalAnalysisUiState {
  if (result.ok) {
    if (result.data.analysis_status === "needs_review") {
      return { status: "needs_review", data: result.data };
    }
    return { status: "analyzed", data: result.data };
  }

  switch (result.error.code) {
    case "not_ready":
      return { status: "not_ready" };
    case "invalid_material_type":
      return { status: "invalid_material_type" };
    case "not_found":
      return { status: "not_found" };
    case "unauthorized":
    case "auth_required":
      return { status: "unauthorized" };
    default:
      return { status: "offline" };
  }
}

function studyPreparationStateFromResult(
  result: ApiResult<BackendStudyMaterialPreparationResponse>
): StudyPreparationUiState {
  if (result.ok) {
    if (result.data.preparation_status === "ready_for_study") {
      return { status: "ready_for_study", data: result.data };
    }
    if (result.data.preparation_status === "needs_review") {
      return { status: "needs_review", data: result.data };
    }
    return { status: "not_ready" };
  }

  switch (result.error.code) {
    case "invalid_material_type":
      return { status: "invalid_material_type" };
    case "not_found":
      return { status: "not_found" };
    case "unauthorized":
    case "auth_required":
      return { status: "unauthorized" };
    default:
      return { status: "offline" };
  }
}

function StudyPreparationAction({
  materialId,
  detail,
  connection
}: {
  materialId: string;
  detail: MaterialDetail;
  connection: BackendConnectionInfo;
}) {
  const [preparationState, setPreparationState] = useState<StudyPreparationUiState>({ status: "idle" });
  const showSessionRequired = connection.state === "auth_required";
  const canPrepare = detail.source === "backend" && !showSessionRequired;

  if (detail.materialType !== "study_material" || (detail.source !== "backend" && !showSessionRequired)) {
    return null;
  }

  const isLoading = preparationState.status === "loading";

  async function handlePrepare() {
    setPreparationState({ status: "loading" });
    const result = await prepareStudyMaterial(materialId);
    setPreparationState(studyPreparationStateFromResult(result));
  }

  return (
    <Card className="min-w-0 border-[rgba(201,169,110,0.18)] bg-[rgba(201,169,110,0.04)]">
      <div className="section-kicker">estudo</div>
      <CardTitle className="mt-5 break-words text-[1.8rem]">Preparação para estudo</CardTitle>
      <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
        Prepare este material para organizar a leitura.
      </p>
      <p className="mt-3 max-w-2xl text-sm leading-7 text-[rgba(232,238,242,0.68)]">
        Esta etapa não gera resumos, questões, simulados nem altera seu progresso.
      </p>

      {showSessionRequired ? (
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <p className="text-sm text-silver">Entre para preparar este material.</p>
          <WorkspaceLink href="/login">Entrar</WorkspaceLink>
        </div>
      ) : (
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={handlePrepare}
            disabled={!canPrepare || isLoading}
            className="inline-flex items-center justify-center rounded-xl border border-[rgba(201,169,110,0.24)] bg-[rgba(201,169,110,0.10)] px-4 py-2 text-sm text-ink transition hover:-translate-y-0.5 hover:bg-[rgba(201,169,110,0.16)] disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0 disabled:hover:bg-[rgba(201,169,110,0.10)]"
          >
            {isLoading ? "Preparando material..." : "Preparar para estudo"}
          </button>
          <WorkspaceLink href="/materials">Voltar para materiais</WorkspaceLink>
        </div>
      )}

      {preparationState.status === "ready_for_study" ? (
        <div className="mt-6 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-4 text-sm leading-7 text-emerald-100">
          <p className="font-medium">Material pronto para estudo.</p>
          <p>
            {preparationState.data.section_count} seções · {preparationState.data.chunk_count} trechos
          </p>
          <p className="mt-2">Próximo passo: estudar este material.</p>
        </div>
      ) : null}

      {preparationState.status === "needs_review" ? (
        <div className="mt-6 rounded-2xl border border-amber-400/20 bg-amber-400/10 p-4 text-sm leading-7 text-amber-100">
          <p className="font-medium">Material preparado, mas precisa de conferência.</p>
          <p>
            {preparationState.data.section_count} seções · {preparationState.data.chunk_count} trechos
          </p>
        </div>
      ) : null}

      {preparationState.status === "not_ready" ? (
        <p className="mt-6 rounded-2xl border border-amber-400/20 bg-amber-400/10 p-4 text-sm leading-7 text-amber-100">
          Este material ainda não está pronto para estudo. Confira se o arquivo tem texto extraível ou envie uma versão textual.
        </p>
      ) : null}

      {preparationState.status === "invalid_material_type" ? (
        <p className="mt-6 rounded-2xl border border-amber-400/20 bg-amber-400/10 p-4 text-sm leading-7 text-amber-100">
          Este arquivo não está classificado como material de estudo.
        </p>
      ) : null}

      {preparationState.status === "not_found" ? (
        <p className="mt-6 rounded-2xl border border-rose-400/20 bg-rose-400/10 p-4 text-sm leading-7 text-rose-100">
          Material não encontrado nesta sessão.
        </p>
      ) : null}

      {preparationState.status === "offline" ? (
        <p className="mt-6 rounded-2xl border border-amber-400/20 bg-amber-400/10 p-4 text-sm leading-7 text-amber-100">
          Não foi possível preparar o material agora.
        </p>
      ) : null}

      {preparationState.status === "unauthorized" ? (
        <p className="mt-6 rounded-2xl border border-amber-400/20 bg-amber-400/10 p-4 text-sm leading-7 text-amber-100">
          Entre para preparar este material.
        </p>
      ) : null}
    </Card>
  );
}

function EditalAnalysisAction({
  materialId,
  detail,
  connection
}: {
  materialId: string;
  detail: MaterialDetail;
  connection: BackendConnectionInfo;
}) {
  const [analysisState, setAnalysisState] = useState<EditalAnalysisUiState>({ status: "idle" });
  const showSessionRequired = connection.state === "auth_required";
  const canAnalyze = detail.source === "backend" && !showSessionRequired;

  if (detail.materialType !== "edital" || (detail.source !== "backend" && !showSessionRequired)) {
    return null;
  }

  const isLoading = analysisState.status === "loading";

  async function handleAnalyze() {
    setAnalysisState({ status: "loading" });
    const result = await analyzeMaterialAsEdital(materialId);
    setAnalysisState(editalAnalysisStateFromResult(result));
  }

  return (
    <Card className="min-w-0 border-[rgba(201,169,110,0.18)] bg-[rgba(201,169,110,0.04)]">
      <div className="section-kicker">edital</div>
      <CardTitle className="mt-5 break-words text-[1.8rem]">Análise do edital</CardTitle>
      <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
        Este arquivo foi marcado como edital. A análise identifica tópicos e referências para orientar o estudo.
      </p>
      <p className="mt-3 max-w-2xl text-sm leading-7 text-[rgba(232,238,242,0.68)]">
        Esta etapa não gera questões, simulados nem altera seu progresso.
      </p>

      {showSessionRequired ? (
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <p className="text-sm text-silver">Entre para analisar este edital.</p>
          <WorkspaceLink href="/login">Entrar</WorkspaceLink>
        </div>
      ) : (
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={!canAnalyze || isLoading}
            className="inline-flex items-center justify-center rounded-xl border border-[rgba(201,169,110,0.24)] bg-[rgba(201,169,110,0.10)] px-4 py-2 text-sm text-ink transition hover:-translate-y-0.5 hover:bg-[rgba(201,169,110,0.16)] disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0 disabled:hover:bg-[rgba(201,169,110,0.10)]"
          >
            {isLoading ? "Analisando edital..." : "Analisar edital"}
          </button>
          <WorkspaceLink href="/materials">Voltar para materiais</WorkspaceLink>
        </div>
      )}

      {analysisState.status === "analyzed" ? (
        <div className="mt-6 rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-4 text-sm leading-7 text-emerald-100">
          <p className="font-medium">Edital analisado.</p>
          <p>
            {analysisState.data.topics_count} tópicos · {analysisState.data.bibliography_count} bibliografia ·{" "}
            {analysisState.data.gaps_count} gaps
          </p>
          <div className="mt-3">
            <WorkspaceLink href="/editais">Ver editais</WorkspaceLink>
          </div>
        </div>
      ) : null}

      {analysisState.status === "needs_review" ? (
        <div className="mt-6 rounded-2xl border border-amber-400/20 bg-amber-400/10 p-4 text-sm leading-7 text-amber-100">
          <p className="font-medium">Edital analisado, mas precisa de conferência.</p>
          <p>
            {analysisState.data.topics_count} tópicos · {analysisState.data.bibliography_count} bibliografia ·{" "}
            {analysisState.data.gaps_count} gaps
          </p>
          <div className="mt-3">
            <WorkspaceLink href="/editais">Ver editais</WorkspaceLink>
          </div>
        </div>
      ) : null}

      {analysisState.status === "not_ready" ? (
        <p className="mt-6 rounded-2xl border border-amber-400/20 bg-amber-400/10 p-4 text-sm leading-7 text-amber-100">
          Este edital ainda não está pronto para análise. Confira se o arquivo tem texto extraível ou envie uma versão textual.
        </p>
      ) : null}

      {analysisState.status === "invalid_material_type" ? (
        <p className="mt-6 rounded-2xl border border-amber-400/20 bg-amber-400/10 p-4 text-sm leading-7 text-amber-100">
          Este material não está classificado como edital.
        </p>
      ) : null}

      {analysisState.status === "not_found" ? (
        <p className="mt-6 rounded-2xl border border-rose-400/20 bg-rose-400/10 p-4 text-sm leading-7 text-rose-100">
          Material não encontrado nesta sessão.
        </p>
      ) : null}

      {analysisState.status === "offline" ? (
        <p className="mt-6 rounded-2xl border border-amber-400/20 bg-amber-400/10 p-4 text-sm leading-7 text-amber-100">
          Não foi possível concluir a análise agora.
        </p>
      ) : null}

      {analysisState.status === "unauthorized" ? (
        <p className="mt-6 rounded-2xl border border-amber-400/20 bg-amber-400/10 p-4 text-sm leading-7 text-amber-100">
          Entre para analisar este edital.
        </p>
      ) : null}
    </Card>
  );
}

export function MaterialDetailReadOnlyClient({ materialId }: { materialId: string }) {
  const [viewModel, setViewModel] = useState<{ connection: BackendConnectionInfo; detail: MaterialDetail | null }>(
    buildFallback(materialId)
  );

  useEffect(() => {
    let active = true;
    void loadMaterialDetail(materialId).then((next) => {
      if (active) {
        setViewModel(next);
      }
    });
    return () => {
      active = false;
    };
  }, [materialId]);

  const { connection, detail } = viewModel;

  if (!detail) {
    return (
      <div className="space-y-8">
        <WorkspaceBackLink href="/materials">Voltar para materiais</WorkspaceBackLink>

        <WorkspaceSourcePanel
          eyebrow="material"
          title="Item não encontrado"
          subtitle="Este conteúdo não está disponível nesta sessão. Consulte os dados de demonstração ou volte para materiais."
          connection={connection}
        />

        <Card className="min-w-0 border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.02)]">
          <CardTitle className="text-[1.8rem] leading-[1.04]">Consulte os materiais disponíveis</CardTitle>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
            Entre para consultar detalhes reais deste material. Enquanto isso, exemplos podem aparecer como apoio.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <WorkspaceLink href="/materials">Ver materiais</WorkspaceLink>
            <WorkspaceLink href="/materials/upload">Enviar material</WorkspaceLink>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <WorkspaceBackLink href="/materials">Voltar para materiais</WorkspaceBackLink>

      <WorkspaceSourcePanel
        eyebrow="material"
        title={detail.title}
        subtitle="Consulte status do material, estrutura segura e avisos de revisão sem expor conteúdo bruto."
        connection={connection}
      />

      <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="min-w-0">
          <div className="flex flex-wrap gap-2">
            <Badge className={sourceBadgeClass(detail.source)}>{sourceLabel(detail.source)}</Badge>
            <Badge className={productStatusClass(detail.processingStatus)}>{detail.processingStatus}</Badge>
            <Badge className="border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.08)] text-silver">
              {detail.typeLabel}
            </Badge>
            {detail.materialTypeLabel ? (
              <Badge className="border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.08)] text-silver">
                {detail.materialTypeLabel}
              </Badge>
            ) : null}
            <Badge className={productStatusClass(detail.reviewState)}>{detail.reviewState}</Badge>
          </div>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                extração
              </div>
              <p className="mt-2 text-sm text-ink">{detail.extractionStatus}</p>
            </div>
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                seções
              </div>
              <p className="mt-2 text-sm text-ink">{detail.sectionsCount ?? 0}</p>
            </div>
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                trechos
              </div>
              <p className="mt-2 text-sm text-ink">{detail.chunksCount ?? 0}</p>
            </div>
          </div>
          <p className="mt-6 text-sm leading-7 text-silver">{detail.sourceNote}</p>
        </Card>

        <Card className="min-w-0">
          <div className="section-kicker">avisos</div>
          <CardTitle className="mt-5 break-words text-[1.8rem]">Revisão necessária</CardTitle>
          {detail.warnings.length ? (
            <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
              {detail.warnings.map((warning) => (
                <li key={warning} className="break-words">
                  • {warning}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-5 text-sm leading-7 text-silver">Nenhum aviso adicional por enquanto.</p>
          )}
          <div className="mt-6">
            <WorkspaceLink href={`/pipeline/${materialId}`}>Ver pipeline</WorkspaceLink>
          </div>
        </Card>
      </section>

      <StudyPreparationAction materialId={materialId} detail={detail} connection={connection} />

      <EditalAnalysisAction materialId={materialId} detail={detail} connection={connection} />

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className="min-w-0">
          <div className="section-kicker">prévia segura</div>
          <CardTitle className="mt-5 break-words text-[1.8rem]">Seções identificadas</CardTitle>
          {detail.sectionPreviews.length ? (
            <div className="mt-5 space-y-3">
              {detail.sectionPreviews.map((section) => (
                <div
                  key={section.id}
                  className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <p className="break-words text-sm text-ink">{section.title}</p>
                    <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-silver">
                      {section.chunkRangeLabel}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-5 text-sm leading-7 text-silver">Nenhuma seção para exibir ainda.</p>
          )}
        </Card>

        <Card className="min-w-0">
          <div className="section-kicker">limites</div>
          <CardTitle className="mt-5 break-words text-[1.8rem]">O que esta tela mostra</CardTitle>
          <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
            <li>• Títulos de seções e contagens seguras.</li>
            <li>• Status de leitura, OCR e revisão.</li>
            <li>• Nenhum texto bruto do documento é exibido.</li>
            <li>• Nenhum conteúdo completo de OCR ou imagem bruta é exibido.</li>
          </ul>
        </Card>
      </section>
    </div>
  );
}
