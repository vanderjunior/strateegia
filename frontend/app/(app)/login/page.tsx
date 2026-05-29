"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { loginWithPassword } from "@/lib/api/auth";
import { loadSessionState } from "@/lib/adapters/session";

function messageForError(code: string): string {
  if (code === "invalid_credentials") {
    return "Credenciais inválidas.";
  }
  if (code === "backend_offline" || code === "network_error") {
    return "Não foi possível conectar ao backend.";
  }
  if (code === "missing_base_url") {
    return "Sessão não configurada.";
  }
  if (code === "validation_failed") {
    return "Preencha usuário e senha para entrar.";
  }
  return "Não foi possível entrar agora.";
}

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [message, setMessage] = useState("Use esta entrada apenas para acesso interno de staging.");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("submitting");
    setMessage("Confirmando sessão.");

    const result = await loginWithPassword({ username, password });

    if (!result.ok) {
      setStatus("error");
      setMessage(messageForError(result.error.code));
      return;
    }

    await loadSessionState({ refresh: true });
    setStatus("success");
    setMessage("Sessão ativa. Redirecionando para o painel.");
    router.push("/dashboard");
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Link href="/dashboard" className="text-sm text-silver transition hover:text-ink">
        Voltar ao painel
      </Link>

      <Card>
        <div className="section-kicker">acesso interno</div>
        <CardTitle className="mt-5 text-[2rem]">Entrar</CardTitle>
        <p className="mt-4 text-sm leading-7 text-silver">
          Use esta tela para acessar dados reais no ambiente interno de staging. Sessões são locais neste
          ambiente; após reiniciar o backend, entre novamente.
        </p>

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <label className="block text-sm text-silver">
            Usuário
            <input
              className="mt-2 w-full rounded-2xl border border-[rgba(168,184,196,0.16)] bg-[rgba(255,255,255,0.04)] px-4 py-3 text-ink outline-none transition focus:border-[rgba(201,169,110,0.42)]"
              autoComplete="username"
              name="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </label>

          <label className="block text-sm text-silver">
            Senha
            <input
              className="mt-2 w-full rounded-2xl border border-[rgba(168,184,196,0.16)] bg-[rgba(255,255,255,0.04)] px-4 py-3 text-ink outline-none transition focus:border-[rgba(201,169,110,0.42)]"
              autoComplete="current-password"
              name="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>

          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" variant="secondary" disabled={status === "submitting"}>
              {status === "submitting" ? "Entrando" : "Entrar"}
            </Button>
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center rounded-xl border border-[rgba(168,184,196,0.12)] bg-transparent px-5 py-3 text-sm text-silver transition hover:border-[rgba(201,169,110,0.24)] hover:text-ink"
            >
              Voltar ao painel
            </Link>
          </div>
        </form>

        <p
          className={`mt-5 rounded-2xl border px-4 py-3 text-sm ${
            status === "error"
              ? "border-amber-400/30 bg-amber-400/12 text-amber-100"
              : status === "success"
                ? "border-emerald-400/30 bg-emerald-400/12 text-emerald-100"
                : "border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.03)] text-silver"
          }`}
          role="status"
        >
          {message}
        </p>
      </Card>
    </div>
  );
}
