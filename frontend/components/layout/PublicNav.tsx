"use client";

import Link from "next/link";

import { MentoriumLogo } from "@/components/brand/MentoriumLogo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function PublicNav() {
  return (
    <header className="sticky top-0 z-40 border-b border-[rgba(168,184,196,0.08)] bg-[rgba(10,21,32,0.78)] backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <MentoriumLogo compact />
        <nav className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-10 text-sm text-silver md:flex">
          <a href="#pipeline" className="transition hover:text-ink">Caminho seguro</a>
          <a href="#funcionalidades" className="transition hover:text-ink">Funcionalidades</a>
          <a href="#como-funciona" className="transition hover:text-ink">Como funciona</a>
          <a href="#acesso-antecipado" className="transition hover:text-ink">Acesso antecipado</a>
        </nav>
        <div className="flex items-center gap-3">
          <Badge>beta fechado</Badge>
          <Link href="/onboarding">
            <Button variant="ghost">Comece sua preparação</Button>
          </Link>
        </div>
      </div>
    </header>
  );
}
