"use client";

import type { PropsWithChildren } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { MentoriumLogo } from "@/components/brand/MentoriumLogo";
import { Badge } from "@/components/ui/badge";

const navigationItems = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Materiais", href: "/materials" },
  { label: "Editais", href: "/editais" },
  { label: "Estudo", href: "/study" },
  { label: "Ciclo" },
  { label: "Questões" },
  { label: "Simulados" },
  { label: "PSCPP", href: "/pscpp" },
  { label: "Runtime" }
] as const;

function headerCopy(pathname: string) {
  if (pathname.startsWith("/materials") || pathname.startsWith("/pipeline")) {
    return {
      eyebrow: pathname.startsWith("/pipeline") ? "mentorium / pipeline" : "mentorium / materiais",
      title: pathname.startsWith("/pipeline")
        ? "Fluxo documental em revisão"
        : "Materiais em leitura controlada"
    };
  }
  if (pathname.startsWith("/editais")) {
    return {
      eyebrow: "mentorium / editais",
      title: "Editais em análise preliminar"
    };
  }
  if (pathname.startsWith("/study/session")) {
    return {
      eyebrow: "mentorium / estudo / sessao",
      title: "Sessão sugerida"
    };
  }
  if (pathname.startsWith("/study")) {
    return {
      eyebrow: "mentorium / estudo",
      title: "Estudo de hoje"
    };
  }
  if (pathname.startsWith("/pscpp/ciclo")) {
    return {
      eyebrow: "mentorium / pscpp / ciclo",
      title: "Ciclo PSCPP sugerido"
    };
  }
  if (pathname.startsWith("/pscpp/questoes")) {
    return {
      eyebrow: "mentorium / pscpp / questoes",
      title: "Orientação de questões PSCPP"
    };
  }
  if (pathname.startsWith("/pscpp/mapa")) {
    return {
      eyebrow: "mentorium / pscpp / mapa",
      title: "Mapa de preparação PSCPP"
    };
  }
  if (pathname.startsWith("/pscpp")) {
    return {
      eyebrow: "mentorium / pscpp",
      title: "Visão geral PSCPP / Praticagem"
    };
  }
  return {
    eyebrow: "mentorium / dashboard",
    title: "Painel de capacidades auditadas"
  };
}

export function AppShell({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const header = headerCopy(pathname);

  return (
    <div className="min-h-screen bg-[var(--color-s3)] text-ink">
      <div className="grid min-h-screen lg:grid-cols-[280px_1fr]">
        <aside className="border-r border-[rgba(168,184,196,0.10)] bg-[rgba(10,21,32,0.9)] px-6 py-8">
          <MentoriumLogo compact />
          <div className="mt-6 space-y-3">
            <Badge>acesso antecipado</Badge>
            <p className="max-w-[220px] text-sm leading-6 text-silver">
              Shell de produto em modo experimental, refletindo apenas capacidades auditadas do backend.
            </p>
          </div>
          <nav className="mt-10 space-y-2">
            {navigationItems.map((item) => {
              const href = "href" in item ? item.href : undefined;
              const active = href
                ? href === "/materials"
                  ? pathname === href || pathname.startsWith(`${href}/`) || pathname.startsWith("/pipeline/")
                  : pathname === href || pathname.startsWith(`${href}/`)
                : false;
              const className = `block rounded-2xl border px-4 py-3 text-sm transition ${
                active
                  ? "border-[rgba(201,169,110,0.26)] bg-[rgba(201,169,110,0.10)] text-ink"
                  : href
                    ? "border-transparent text-silver hover:border-[rgba(168,184,196,0.10)] hover:bg-[rgba(255,255,255,0.02)]"
                    : "border-transparent text-[rgba(168,184,196,0.45)]"
              }`;

              if (!href) {
                return (
                  <div key={item.label} className={className}>
                    {item.label}
                  </div>
                );
              }

              return (
                <Link key={item.label} href={href} className={className}>
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </aside>
        <div className="bg-radial-shell">
          <header className="flex items-center justify-between border-b border-[rgba(168,184,196,0.08)] bg-[rgba(10,21,32,0.44)] px-6 py-5 lg:px-10">
            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.24em] text-silver">
                {header.eyebrow}
              </div>
              <h1 className="mt-2 font-serif text-3xl text-ink">{header.title}</h1>
            </div>
            <Badge>read-only beta</Badge>
          </header>
          <main className="px-6 py-8 lg:px-10">{children}</main>
        </div>
      </div>
    </div>
  );
}
