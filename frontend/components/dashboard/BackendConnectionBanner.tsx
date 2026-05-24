"use client";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { BackendConnectionInfo } from "@/lib/api/types";

function bannerTone(state: BackendConnectionInfo["state"]): string {
  switch (state) {
    case "connected":
      return "border-emerald-400/20 bg-emerald-400/10";
    case "auth_required":
      return "border-sky-400/20 bg-sky-400/10";
    case "offline":
      return "border-amber-400/20 bg-amber-400/10";
    case "unsupported":
      return "border-violet-400/20 bg-violet-400/10";
    case "error":
      return "border-rose-400/20 bg-rose-400/10";
    default:
      return "border-[rgba(201,169,110,0.16)] bg-[rgba(201,169,110,0.08)]";
  }
}

export function BackendConnectionBanner({ connection }: { connection: BackendConnectionInfo }) {
  return (
    <Card className={`${bannerTone(connection.state)} p-0`}>
      <div className="naval-window-bar rounded-t-[28px] border-b-[rgba(168,184,196,0.1)]">
        <span className="naval-window-dot bg-[#e17d69]" />
        <span className="naval-window-dot bg-[#d6c477]" />
        <span className="naval-window-dot bg-[#8fc9a9]" />
        <div className="window-url">{connection.endpoint ?? "frontend / read-only bridge"}</div>
      </div>
      <div className="p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="section-kicker">
              backend status
            </div>
            <h3 className="mt-3 font-serif text-2xl text-ink">{connection.title}</h3>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-silver">{connection.detail}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge>{connection.state.replaceAll("_", " ")}</Badge>
            <Badge className="border-[rgba(168,184,196,0.18)] bg-[rgba(168,184,196,0.08)] text-silver">
              {connection.source}
            </Badge>
          </div>
        </div>
      </div>
    </Card>
  );
}
