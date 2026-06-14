"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import {
  SESSION_STATE_CHANGED_EVENT,
  buildDefaultSessionState,
  loadSessionState,
  notifySessionStateChanged
} from "@/lib/adapters/session";
import { logoutCurrentSession } from "@/lib/api/auth";
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

function displaySessionLabel(sessionState: SessionState): string {
  if (sessionState.status === "backend_offline") {
    return "Indisponível";
  }
  if (sessionState.status === "unauthenticated") {
    return "Entrar para continuar";
  }
  return sessionState.label;
}

function displaySessionDescription(sessionState: SessionState): string {
  if (sessionState.status === "authenticated") {
    return sessionState.userLabel ? `Olá, ${sessionState.userLabel}.` : "Você está conectado.";
  }
  if (sessionState.status === "unauthenticated") {
    return "Entre para acessar seus materiais e orientações.";
  }
  if (sessionState.status === "backend_offline") {
    return "Não foi possível carregar seus dados agora.";
  }
  if (sessionState.status === "mock_mode") {
    return "Conheça o fluxo antes de entrar.";
  }
  return "Entre quando a sessão estiver disponível.";
}

export function SessionStatusNotice({
  variant = "sidebar"
}: {
  variant?: "sidebar" | "dashboard";
}) {
  const [sessionState, setSessionState] = useState<SessionState>(buildDefaultSessionState());
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [logoutPending, setLogoutPending] = useState(false);

  useEffect(() => {
    let active = true;

    function refreshSessionNotice() {
      void loadSessionState({ refresh: true }).then((nextState) => {
        if (active) {
          setSessionState(nextState);
        }
      });
    }

    refreshSessionNotice();
    window.addEventListener(SESSION_STATE_CHANGED_EVENT, refreshSessionNotice);

    return () => {
      active = false;
      window.removeEventListener(SESSION_STATE_CHANGED_EVENT, refreshSessionNotice);
    };
  }, []);

  async function refreshSessionAfterAction() {
    const nextState = await loadSessionState({ refresh: true });
    setSessionState(nextState);
    notifySessionStateChanged();
  }

  async function handleLogout() {
    setLogoutPending(true);
    setActionMessage(null);
    const result = await logoutCurrentSession();

    if (!result.ok) {
      setLogoutPending(false);
      setActionMessage(
        result.error.code === "backend_offline"
          ? "Não foi possível encerrar a sessão agora."
          : "Não foi possível encerrar a sessão agora."
      );
      return;
    }

    await refreshSessionAfterAction();
    setLogoutPending(false);
    setActionMessage("Você saiu.");
  }

  const actionControl =
    sessionState.status === "authenticated" ? (
      <button
        type="button"
        className="rounded-xl border border-[rgba(168,184,196,0.12)] px-3 py-2 text-xs uppercase tracking-[0.16em] text-silver transition hover:border-[rgba(201,169,110,0.24)] hover:text-ink disabled:opacity-60"
        disabled={logoutPending}
        onClick={() => {
          void handleLogout();
        }}
      >
        {logoutPending ? "Saindo" : "Sair"}
      </button>
    ) : sessionState.status === "unauthenticated" || sessionState.status === "unsupported" ? (
      <Link
        href="/login"
        className="rounded-xl border border-[rgba(201,169,110,0.24)] bg-[rgba(201,169,110,0.10)] px-3 py-2 text-xs uppercase tracking-[0.16em] text-ink transition hover:bg-[rgba(201,169,110,0.16)]"
      >
        Entrar
      </Link>
    ) : null;

  if (variant === "dashboard") {
    return (
      <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-silver">sua conta</div>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-[rgba(232,238,242,0.72)]">
              {displaySessionDescription(sessionState)}
            </p>
          </div>
          <div className="flex max-w-full flex-wrap items-center gap-2">
            <Badge className={statusBadgeClass(sessionState.status)}>{displaySessionLabel(sessionState)}</Badge>
            {actionControl}
          </div>
        </div>
        {actionMessage ? <p className="mt-3 text-sm text-silver">{actionMessage}</p> : null}
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
      <div className="flex flex-wrap gap-2">
        <Badge className={statusBadgeClass(sessionState.status)}>{displaySessionLabel(sessionState)}</Badge>
        {actionControl}
      </div>
      <p className="mt-4 text-sm leading-7 text-silver">{displaySessionDescription(sessionState)}</p>
      {sessionState.userLabel ? (
        <p className="mt-3 text-xs uppercase tracking-[0.18em] text-[rgba(232,238,242,0.62)]">
          {sessionState.userLabel}
        </p>
      ) : null}
      {actionMessage ? <p className="mt-3 text-sm text-silver">{actionMessage}</p> : null}
    </div>
  );
}
