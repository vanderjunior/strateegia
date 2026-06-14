"use client";

import { useEffect, useState } from "react";

import { DashboardStudyBridge } from "@/components/dashboard/DashboardStudyBridge";
import { SessionStatusNotice } from "@/components/layout/SessionStatusNotice";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { WorkspaceLink } from "@/components/workspace/WorkspaceShared";
import type { SessionState } from "@/lib/api/types";
import {
  buildDefaultRealUserStudyReadiness,
  loadRealUserStudyReadiness,
  type RealUserStudyReadiness
} from "@/lib/adapters/real-user-state";
import { buildDefaultSessionState, loadSessionState } from "@/lib/adapters/session";

function UnauthenticatedDashboardPanel() {
  return (
    <div className="space-y-6">
      <SessionStatusNotice variant="dashboard" />
      <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
        <Badge>entrar</Badge>
        <CardTitle className="mt-5 max-w-3xl break-words text-[2rem] leading-[1.02] sm:text-[2.35rem]">
          Entre para ver seus materiais, edital e caminho de estudo.
        </CardTitle>
        <p className="mt-4 max-w-2xl text-sm leading-8 text-silver">
          Entre para continuar de onde parou.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <WorkspaceLink href="/login">Entrar</WorkspaceLink>
          <WorkspaceLink href="/onboarding">Conhecer o fluxo</WorkspaceLink>
        </div>
      </Card>
    </div>
  );
}

function DashboardNextStepCard({ readiness }: { readiness: RealUserStudyReadiness }) {
  const title = readiness.editalAnalysisDescription;
  const detail =
    readiness.editalAnalysisState === "analysis_needs_review"
      ? "Confira a análise antes de usar o edital no caminho de estudo."
      : readiness.editalAnalysisState === "analysis_unavailable"
        ? "Não foi possível carregar o edital agora. Tente novamente em instantes."
        : readiness.editalAnalysisState === "edital_uploaded_not_analyzed"
          ? "Analise o edital para definir o conteúdo da sua preparação."
          : "Envie seu edital para definir o conteúdo da sua preparação.";
  const primaryLabel = readiness.shouldShowEditalUploadCTA ? "Enviar edital" : "Enviar materiais de estudo";

  return (
    <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
      <div className="section-kicker">próximo passo</div>
      <CardTitle className="mt-5 max-w-3xl break-words text-[1.9rem] leading-[1.02]">
        {title}
      </CardTitle>
      <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
        {detail}
      </p>
      <div className="mt-6 flex flex-wrap gap-3">
        <WorkspaceLink href="/materials/upload">{primaryLabel}</WorkspaceLink>
        <WorkspaceLink href="/materials">Ver materiais</WorkspaceLink>
      </div>
    </Card>
  );
}

function MaterialsByTypeSummary({ readiness }: { readiness: RealUserStudyReadiness }) {
  return (
    <Card className="border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.02)]">
      <div className="section-kicker">seus materiais</div>
      <CardTitle className="mt-5 text-[1.75rem] leading-[1.04]">Materiais enviados por tipo</CardTitle>
      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
          <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">editais enviados</div>
          <p className="mt-3 font-serif text-3xl text-ink">{readiness.editalMaterialsCount}</p>
        </div>
        <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
          <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">materiais de estudo</div>
          <p className="mt-3 font-serif text-3xl text-ink">{readiness.studyMaterialsCount}</p>
        </div>
        <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
          <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">total enviado</div>
          <p className="mt-3 font-serif text-3xl text-ink">{readiness.materialsCount}</p>
        </div>
      </div>
      {readiness.hasRealStudyMaterial ? (
        <p className="mt-5 text-sm leading-7 text-silver">
          Materiais de estudo enviados: {readiness.studyMaterialsCount}. Prepare-os quando quiser começar pelos blocos.
        </p>
      ) : (
        <p className="mt-5 text-sm leading-7 text-silver">
          Envie um material de estudo para começar.
        </p>
      )}
    </Card>
  );
}

export function DashboardReadOnlyClient() {
  const [sessionState, setSessionState] = useState<SessionState>(buildDefaultSessionState());
  const [readiness, setReadiness] = useState<RealUserStudyReadiness>(buildDefaultRealUserStudyReadiness());

  useEffect(() => {
    let active = true;

    void loadSessionState({ refresh: true }).then((next) => {
      if (active) {
        setSessionState(next);
      }
    });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let active = true;

    void loadRealUserStudyReadiness().then((next) => {
      if (active) {
        setReadiness(next);
      }
    });

    return () => {
      active = false;
    };
  }, []);

  if (sessionState.status !== "authenticated") {
    return <UnauthenticatedDashboardPanel />;
  }

  return (
    <div className="space-y-8">
      <div className="space-y-4">
        <SessionStatusNotice variant="dashboard" />
      </div>

      {readiness.canShowConcreteStudyPlan ? <DashboardStudyBridge /> : <DashboardNextStepCard readiness={readiness} />}

      <MaterialsByTypeSummary readiness={readiness} />

      <Card className="border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.02)]">
        <div className="section-kicker">estado do edital</div>
        <CardTitle className="mt-5 text-[1.75rem] leading-[1.04]">
          {readiness.editalAnalysisLabel}
        </CardTitle>
        <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
          {readiness.editalAnalysisDescription}
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <WorkspaceLink href="/materials/upload">Enviar edital</WorkspaceLink>
          <WorkspaceLink href="/editais">Ver editais</WorkspaceLink>
        </div>
      </Card>
    </div>
  );
}
