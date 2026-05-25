import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import type { ApiSource, BackendConnectionInfo, WorkspaceSummaryMetric } from "@/lib/api/types";
import { sourceLabel } from "@/lib/adapters/capabilities";

export function sourceBadgeClass(source: ApiSource): string {
  switch (source) {
    case "backend":
      return "border-emerald-400/30 bg-emerald-400/12 text-emerald-100";
    case "offline":
      return "border-amber-400/30 bg-amber-400/12 text-amber-100";
    case "unsupported":
      return "border-rose-400/30 bg-rose-400/12 text-rose-100";
    default:
      return "border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.10)] text-silver";
  }
}

export function productStatusClass(label: string): string {
  const normalized = label.toLowerCase();

  if (
    normalized.includes("processado") ||
    normalized.includes("pronto") ||
    normalized.includes("cobertura boa") ||
    normalized.includes("suportado") ||
    normalized.includes("concluído") ||
    normalized.includes("validado")
  ) {
    return "border-emerald-400/30 bg-emerald-400/12 text-emerald-100";
  }

  if (
    normalized.includes("ocr") ||
    normalized.includes("parcial") ||
    normalized.includes("gap") ||
    normalized.includes("conferência") ||
    normalized.includes("validação") ||
    normalized.includes("necessário") ||
    normalized.includes("revisão") ||
    normalized.includes("candidato")
  ) {
    return "border-amber-400/30 bg-amber-400/12 text-amber-100";
  }

  if (normalized.includes("não")) {
    return "border-rose-400/30 bg-rose-400/12 text-rose-100";
  }

  return "border-violet-400/30 bg-violet-400/12 text-violet-100";
}

export function WorkspaceSourcePanel({
  eyebrow,
  title,
  subtitle,
  connection
}: {
  eyebrow: string;
  title: string;
  subtitle: string;
  connection: BackendConnectionInfo;
}) {
  return (
    <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-3xl">
          <div className="section-kicker">{eyebrow}</div>
          <CardTitle className="mt-5 text-[2.2rem]">{title}</CardTitle>
          <p className="mt-4 max-w-2xl text-sm leading-8 text-silver">{subtitle}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge className={sourceBadgeClass(connection.source)}>{sourceLabel(connection.source)}</Badge>
          <Badge className="border-[rgba(201,169,110,0.22)] bg-[rgba(201,169,110,0.10)] text-ink">
            {connection.title}
          </Badge>
        </div>
      </div>
      <p className="mt-5 text-sm leading-7 text-[rgba(232,238,242,0.68)]">{connection.detail}</p>
    </Card>
  );
}

export function WorkspaceSummaryGrid({ items }: { items: WorkspaceSummaryMetric[] }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => (
        <Card key={item.id} className="h-full">
          <div className="font-mono text-[11px] uppercase tracking-[0.22em] text-silver">
            resumo
          </div>
          <div className="mt-5 font-serif text-4xl text-ink">{item.value}</div>
          <p className="mt-3 text-sm text-silver">{item.label}</p>
          <p className="mt-2 text-sm leading-7 text-[rgba(232,238,242,0.68)]">{item.detail}</p>
        </Card>
      ))}
    </div>
  );
}

export function WorkspaceLink({
  href,
  children
}: {
  href: string;
  children: string;
}) {
  return (
    <Link
      href={href}
      className="inline-flex items-center justify-center rounded-xl border border-[rgba(201,169,110,0.24)] bg-[rgba(201,169,110,0.10)] px-4 py-2 text-sm text-ink transition hover:-translate-y-0.5 hover:bg-[rgba(201,169,110,0.16)]"
    >
      {children}
    </Link>
  );
}
