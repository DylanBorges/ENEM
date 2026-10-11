"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, token } from "@/lib/api";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";

type Area = { area: string; estimated_score: number; raw_correct: number; calibration_id: string };
type Attempt = { attempt_id: string; date: string; areas: Area[] };
type Essay = { submission_id: string; topic: string; total_score: number | null; created_at: string };
type Dashboard = { evolution: Attempt[]; recent_essays: Essay[]; disclaimer: string };

export default function HistoryPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const [signedIn, setSignedIn] = useState(false);
  useEffect(() => {
    setSignedIn(Boolean(token()));
    if (token()) api<Dashboard>("/dashboard/me").then(setData).catch(caught => setError(caught.message));
  }, []);
  return <main className="mx-auto max-w-5xl space-y-6">
    <DisclaimerBanner />
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
      <h1 className="text-2xl font-bold">Meu histórico</h1>
      {!signedIn && <p className="mt-4 text-sm"><Link href="/login" className="font-semibold text-blue-700 underline">Entre na sua conta</Link> para consultar seus registros.</p>}
      {error && <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      {data && <>
        <p className="mt-2 text-sm text-slate-600">{data.disclaimer}</p>
        <h2 className="mt-8 text-lg font-bold">Simulados</h2>
        {data.evolution.length === 0 ? <p className="mt-3 text-sm text-slate-600">Nenhum simulado calculado ainda.</p> : <ul className="mt-3 divide-y divide-slate-200">{data.evolution.map(attempt => <li key={attempt.attempt_id} className="py-4"><Link href={`/result/${attempt.attempt_id}`} className="font-semibold text-blue-700 underline">{new Date(attempt.date).toLocaleDateString("pt-BR")}</Link><div className="mt-1 flex flex-wrap gap-3 text-sm">{attempt.areas.map(area => <span key={area.area}>{area.area}: {area.estimated_score.toFixed(1)} ({area.raw_correct} acertos)</span>)}</div></li>)}</ul>}
        <h2 className="mt-8 text-lg font-bold">Redações</h2>
        {data.recent_essays.length === 0 ? <p className="mt-3 text-sm text-slate-600">Nenhuma redação enviada ainda.</p> : <ul className="mt-3 divide-y divide-slate-200">{data.recent_essays.map(essay => <li key={essay.submission_id} className="py-3 text-sm"><span className="font-semibold">{essay.topic}</span> · {essay.total_score === null ? "Sem avaliação" : `${essay.total_score} pontos estimados`}</li>)}</ul>}
      </>}
    </section>
  </main>;
}
