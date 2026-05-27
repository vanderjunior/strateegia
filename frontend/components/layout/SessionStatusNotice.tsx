"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { loadSessionState, buildDefaultSessionState } from "@/lib/adapters/session";
import type { SessionState } from "@/lib/api/types";

function statusBadgeClass(status: SessionState["status"]): string {
  switch (status) {
    case "authenticated":
      return "border-emerald-400/30 bg-emerald-400/12 text-emerald-100";
    case "backend_offline":
      return "border-amber-400/30 bg-amber-400/12 text-amber-100";
    case "unsupported":
      return "border-violet-400/30 bg-violet-400/12 text-violet-100";
    case "mock_mode":
      return "border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.10)] text-silver";
    default:
      return "border-sky-400/30 bg-sky-400/12 text-sky-100";
  }
}

function statusSourceLabel(sessionState: SessionState): string {
  switch (sessionState.status) {
    case "authenticated":
      return "Dados auditados";
    case "unauthenticated":
      return "Requer sessão";
    case "backend_offline":
      return "Consulta local";
    case "unsupported":
      return "Painel em validação";
    default:
      return "Dados de demonstração";
  }
}

export function SessionStatusNotice({
  variant = "sidebar"
}: {
  variant?: "sidebar" | "dashboard";
}) {
  const [sessionState, setSessionState] = useState<SessionState>(buildDefaultSessionState());

  useEffect(() => {
    let active = true;

    void loadSessionState().then((nextState) => {
      if (active) {
        setSessionState(nextState);
      }
    });

    return () => {
      active = false;
    };
  }, []);

  if (variant === "dashboard") {
    return (
      <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-silver">
              sessão da aplicação
            </div>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-[rgba(232,238,242,0.72)]">
              {sessionState.status === "authenticated"
                ? "A sessão atual permite consultar dados reais nas áreas protegidas, sem alterar seu progresso automaticamente."
                : sessionState.status === "unauthenticated"
                  ? "Para usar dados reais, será necessário entrar na aplicação. Enquanto isso, o painel usa dados de demonstração."
                  : sessionState.status === "backend_offline"
                    ? "Não foi possível confirmar a sessão agora. Enquanto isso, o painel usa dados de demonstração."
                    : sessionState.status === "mock_mode"
                      ? "Este ambiente usa dados de demonstração e não consulta a sessão real."
                      : "A sessão real ainda não está configurada neste ambiente. O painel segue em modo de demonstração."}
            </p>
          </div>
          <div className="flex max-w-full flex-wrap gap-2">
            <Badge className={statusBadgeClass(sessionState.status)}>{sessionState.label}</Badge>
            <Badge className="border-[rgba(168,184,196,0.18)] bg-[rgba(168,184,196,0.08)] text-silver">
              {statusSourceLabel(sessionState)}
            </Badge>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
      <div className="flex flex-wrap gap-2">
        <Badge className={statusBadgeClass(sessionState.status)}>{sessionState.label}</Badge>
        <Badge className="border-[rgba(168,184,196,0.18)] bg-[rgba(168,184,196,0.08)] text-silver">
          {statusSourceLabel(sessionState)}
        </Badge>
      </div>
      <p className="mt-4 text-sm leading-7 text-silver">{sessionState.description}</p>
      {sessionState.userLabel ? (
        <p className="mt-3 text-xs uppercase tracking-[0.18em] text-[rgba(232,238,242,0.62)]">
          sessão reconhecida: {sessionState.userLabel}
        </p>
      ) : null}
    </div>
  );
}
