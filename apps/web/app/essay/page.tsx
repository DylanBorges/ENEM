"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { api, token } from "@/lib/api";

type Competency = { competency: string; predicted_score: number; confidence: number; feedback: string; evidence_spans: string[]; requires_human_review: boolean };
type Grade = { submission_id: string; total_score: number; competencies: Competency[]; disclaimer: string; model_version: string; official: false };
const names: Record<string, string> = { C1: "Escrita formal", C2: "Tema e repertório", C3: "Argumentação", C4: "Coesão", C5: "Intervenção" };

export default function EssayPage() {
  const [topic, setTopic] = useState("");
  const [essay, setEssay] = useState("");
  const [grade, setGrade] = useState<Grade | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [review, setReview] = useState("");
  const [signedIn, setSignedIn] = useState(false);
  useEffect(() => setSignedIn(Boolean(token())), []);

  async function evaluate() {
    setError(""); setGrade(null); setBusy(true);
    try {
      const created = await api<{ id: string }>("/essays", { method: "POST", body: JSON.stringify({ topic, text: essay, source: "typed" }) });
      const result = await api<Grade>(`/essays/${created.id}/pregrade`, { method: "POST" });
      setGrade(result);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Não foi possível avaliar a redação");
    } finally { setBusy(false); }
  }

  async function requestReview() {
    if (!grade) return;
    try {
      const result = await api<{ status: string }>(`/essays/${grade.submission_id}/human-review`, { method: "POST", body: "{}" });
      setReview(result.status === "PENDING_HUMAN_REVIEW" ? "Solicitação registrada. Ainda não há atribuição automática a revisores." : result.status);
    } catch (caught) { setReview(caught instanceof Error ? caught.message : "Falha ao solicitar revisão"); }
  }

  return <main className="mx-auto max-w-4xl space-y-6">
    <DisclaimerBanner />
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
      <h1 className="text-2xl font-bold">Corrigir minha redação</h1>
      <p className="mt-2 text-sm text-slate-600">Escreva sobre um tema livre. A avaliação só aparece quando o serviço de IA responder com cinco competências e evidências presentes no texto.</p>
      {!signedIn && <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">Para salvar e avaliar, <Link href="/login" className="font-semibold underline">entre na sua conta</Link>.</p>}
      <div className="mt-6 space-y-4">
        <label className="block text-sm font-semibold">Tema<input value={topic} onChange={event => setTopic(event.target.value)} maxLength={255} className="mt-1 block w-full rounded-lg border border-slate-300 p-3 font-normal" /></label>
        <label className="block text-sm font-semibold">Sua redação<textarea value={essay} onChange={event => setEssay(event.target.value)} rows={14} maxLength={30000} className="mt-1 block w-full rounded-lg border border-slate-300 p-3 font-normal leading-relaxed" /></label>
        <p className="text-sm text-slate-500">{essay.trim() ? essay.trim().split(/\s+/).length : 0} palavras. O texto digitado não informa a quantidade de linhas da folha oficial.</p>
        {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</p>}
        <button onClick={evaluate} disabled={busy || !signedIn || topic.trim().length < 3 || essay.length < 100} className="rounded-lg bg-blue-700 px-5 py-3 font-semibold text-white disabled:opacity-50">{busy ? "Avaliando..." : "Avaliar redação"}</button>
      </div>
    </section>
    {grade && <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8" aria-live="polite">
      <p className="text-sm font-semibold text-blue-700">Nota estimada · não oficial</p>
      <h2 className="mt-1 text-4xl font-bold">{grade.total_score} <span className="text-lg font-normal text-slate-500">/ 1000</span></h2>
      <p className="mt-2 text-sm text-slate-600">{grade.disclaimer}</p>
      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {grade.competencies.map(comp => <article key={comp.competency} className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex justify-between gap-3"><h3 className="font-semibold">{comp.competency} · {names[comp.competency]}</h3><strong>{comp.predicted_score}/200</strong></div>
          <p className="mt-2 text-sm text-slate-700">{comp.feedback}</p>
          {comp.evidence_spans.map((span, index) => <blockquote key={index} className="mt-2 border-l-2 border-blue-500 pl-3 text-sm italic text-slate-600">{span}</blockquote>)}
          {comp.requires_human_review && <p className="mt-2 text-sm font-medium text-amber-800">Revisão humana recomendada</p>}
        </article>)}
      </div>
      <p className="mt-4 text-xs text-slate-500">Modelo e rubrica: {grade.model_version}</p>
      <button onClick={requestReview} className="mt-5 rounded-lg border border-slate-300 px-4 py-3 text-sm font-semibold">Solicitar revisão humana</button>
      {review && <p role="status" className="mt-2 text-sm">{review}</p>}
    </section>}
  </main>;
}
