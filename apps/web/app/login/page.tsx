"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [name, setName] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (registering) await api("/auth/register", { method: "POST", body: JSON.stringify({ email, password, full_name: name }) });
      const result = await api<{ access_token: string }>("/auth/login", {
        method: "POST", body: JSON.stringify({ email, password }),
      });
      sessionStorage.setItem("access_token", result.access_token);
      router.push("/simulator");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Falha ao entrar");
    } finally {
      setLoading(false);
    }
  }

  return <div className="mx-auto max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <h1 className="text-2xl font-bold">{registering ? "Criar conta" : "Entrar"}</h1>
    <p className="mt-2 text-sm text-slate-600">Use sua conta para salvar simulados e redações.</p>
    <form onSubmit={submit} className="mt-6 space-y-4">
      {registering && <label className="block text-sm font-medium">Nome<input required autoComplete="name" value={name} onChange={event => setName(event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 p-3" /></label>}
      <label className="block text-sm font-medium">E-mail<input type="email" required autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 p-3" /></label>
      <label className="block text-sm font-medium">Senha<input type="password" required autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} className="mt-1 block w-full rounded-lg border border-slate-300 p-3" /></label>
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      {loading && <p role="status" className="text-sm text-slate-600">Conectando ao servidor. Na hospedagem gratuita, isso pode levar cerca de 1 minuto.</p>}
      <button disabled={loading} className="w-full rounded-lg bg-blue-700 p-3 font-semibold text-white disabled:opacity-50">{loading ? "Aguarde..." : registering ? "Criar conta e entrar" : "Entrar"}</button>
    </form>
    <div className="mt-4 flex flex-col gap-2 pt-2 border-t border-slate-100">
      <button
        type="button"
        onClick={() => { setEmail("estudante@enem.com"); setPassword("Senha@123"); }}
        className="text-xs text-slate-500 hover:text-slate-800 underline text-left"
      >
        Preencher com usuário de teste (estudante@enem.com)
      </button>
      <button onClick={() => { setRegistering(!registering); setError(""); }} className="text-sm font-semibold text-blue-700 underline text-left">{registering ? "Já tenho conta" : "Criar uma conta"}</button>
    </div>
  </div>;
}
