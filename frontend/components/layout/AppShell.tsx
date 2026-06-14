"use client";

import type { PropsWithChildren } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { MentoriumLogo } from "@/components/brand/MentoriumLogo";
import { SessionStatusNotice } from "@/components/layout/SessionStatusNotice";
import { Badge } from "@/components/ui/badge";

const navigationItems = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Começar", href: "/onboarding" },
  { label: "Materiais", href: "/materials" },
  { label: "Editais", href: "/editais" },
  { label: "Estudo", href: "/study", status: "Caminho de estudo" },
  { label: "Ciclo", href: "/pscpp/ciclo", status: "Depois do edital" },
  { label: "Questões", status: "Mais tarde" },
  { label: "Avaliações", status: "Mais tarde" },
  { label: "PSCPP", href: "/pscpp", status: "Referência" },
  { label: "Execução", status: "Mais tarde" }
] as const;

function headerCopy(pathname: string) {
  if (pathname.startsWith("/login")) {
    return {
      eyebrow: "Acesso",
      title: "Entre para continuar"
    };
  }
  if (pathname.startsWith("/onboarding")) {
    return {
      eyebrow: "Preparação",
      title: "Comece sua preparação"
    };
  }
  if (pathname.startsWith("/materials") || pathname.startsWith("/pipeline")) {
    return {
      eyebrow: "Materiais",
      title: pathname.startsWith("/pipeline") ? "Acompanhamento do material" : "Materiais"
    };
  }
  if (pathname.startsWith("/editais")) {
    return {
      eyebrow: "Editais",
      title: "Editais"
    };
  }
  if (pathname.startsWith("/study/session")) {
    return {
      eyebrow: "Estudo",
      title: "Orientação de estudo"
    };
  }
  if (pathname.startsWith("/study")) {
    return {
      eyebrow: "Estudo",
      title: "Seu caminho de estudo"
    };
  }
  if (pathname.startsWith("/pscpp/ciclo")) {
    return {
      eyebrow: "PSCPP",
      title: "Ciclo aguardando edital analisado"
    };
  }
  if (pathname.startsWith("/pscpp/questoes")) {
    return {
      eyebrow: "PSCPP",
      title: "Questões ainda não disponíveis"
    };
  }
  if (pathname.startsWith("/pscpp/mapa")) {
    return {
      eyebrow: "PSCPP",
      title: "Mapa PSCPP de referência"
    };
  }
  if (pathname.startsWith("/pscpp")) {
    return {
      eyebrow: "PSCPP",
      title: "Visão geral PSCPP / Praticagem"
    };
  }
  return {
    eyebrow: "Preparação",
    title: "Painel de preparação"
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
            <Badge>preparação guiada</Badge>
            <p className="max-w-[220px] text-sm leading-6 text-silver">
              Materiais, edital e estudo organizados no mesmo lugar.
            </p>
            <SessionStatusNotice />
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

              const content = (
                <>
                  <span>{item.label}</span>
                  {"status" in item ? (
                    <span className="mt-1 block text-[11px] leading-4 text-[rgba(168,184,196,0.58)]">
                      {item.status}
                    </span>
                  ) : null}
                </>
              );

              if (!href) {
                return (
                  <div key={item.label} className={className} aria-disabled="true">
                    {content}
                  </div>
                );
              }

              return (
                <Link key={item.label} href={href} className={className}>
                  {content}
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
            <Badge>em revisão</Badge>
          </header>
          <main className="px-6 py-8 lg:px-10">{children}</main>
        </div>
      </div>
    </div>
  );
}
