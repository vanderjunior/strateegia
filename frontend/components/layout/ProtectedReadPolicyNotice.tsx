"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { buildDefaultSessionState, loadSessionState } from "@/lib/adapters/session";
import { protectedReadBadgeClass, resolveProtectedReadPolicy } from "@/lib/auth/protected-read-policy";
import type { ProtectedReadPolicy, SessionState } from "@/lib/api/types";

export function ProtectedReadPolicyNotice({
  surfaceLabel
}: {
  surfaceLabel: string;
}) {
  const [sessionState, setSessionState] = useState<SessionState>(buildDefaultSessionState());
  const [policy, setPolicy] = useState<ProtectedReadPolicy>(() =>
    resolveProtectedReadPolicy(buildDefaultSessionState())
  );

  useEffect(() => {
    let active = true;

    void loadSessionState().then((nextState) => {
      if (active) {
        setSessionState(nextState);
        setPolicy(resolveProtectedReadPolicy(nextState));
      }
    });

    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-silver">
            leitura protegida
          </div>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-[rgba(232,238,242,0.72)]">
            {surfaceLabel}: {policy.recommendedUserCopy}
          </p>
        </div>
        <div className="flex max-w-full flex-wrap gap-2">
          <Badge className={protectedReadBadgeClass(policy.badgeTone)}>{policy.label}</Badge>
          <Badge className="border-[rgba(168,184,196,0.18)] bg-[rgba(168,184,196,0.08)] text-silver">
            {policy.mode === "real_authenticated"
              ? "Dados reais"
              : policy.mode === "requires_session"
                ? "Dados de demonstração"
                : policy.mode === "backend_offline"
                  ? "Demonstração"
                  : policy.mode === "unsupported"
                    ? "Demonstração"
                    : "Dados de demonstração"}
          </Badge>
        </div>
      </div>
      <p className="mt-4 text-sm leading-7 text-silver">{policy.description}</p>
      {sessionState.userLabel && policy.canUseRealData ? (
        <p className="mt-3 text-xs uppercase tracking-[0.18em] text-[rgba(232,238,242,0.62)]">
          sessão reconhecida: {sessionState.userLabel}
        </p>
      ) : null}
    </div>
  );
}
