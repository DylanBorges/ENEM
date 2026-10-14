"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { emptyQuestionFilters, questionCatalogHref, questionDetailHref, questionFilterQuery, readQuestionFilters, type QuestionFilters } from "@/lib/questionFilters";

type Block = { type: "text" | "image"; value: string; alt?: string };
type Alternative = { letter: string; text: string; image: string | null };
type Question = {
  id: string; year: number; day: number; area_name: string; subject: string | null;
  subject_classification: "automatic" | "exam" | null; position: number; booklet_color: string;
  difficulty: "facil" | "media" | "dificil"; content_available: boolean;
  blocks?: Block[]; alternatives?: Alternative[]; content_source?: string;
  source_position?: number; source_booklet?: string;
};
type AnswerResult = { selected_answer: string; correct_answer: string | null; correct: boolean | null; annulled: boolean };
type Neighbor = { id: string; position: number };
type Neighbors = { previous: Neighbor | null; next: Neighbor | null };
const difficultyLabels = { facil: "Fácil", media: "Média", dificil: "Difícil" };

function QuestionNavigation({ neighbors, filters, label }: { neighbors: Neighbors | null; filters: QuestionFilters; label: string }) {
  return <nav aria-label={label} className="grid grid-cols-2 gap-2 sm:gap-3">
    {neighbors?.previous ? <Link href={questionDetailHref(neighbors.previous.id, filters)} className="flex min-h-14 min-w-0 flex-col justify-center rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-blue-700 hover:border-blue-400 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-300 sm:px-4">
      <span>← Anterior</span><span className="text-xs font-normal text-slate-600">Questão {neighbors.previous.position}</span>
    </Link> : <span aria-disabled="true" className="flex min-h-14 items-center rounded-xl border border-slate-200 bg-slate-100 px-3 text-sm text-slate-500 sm:px-4">← Anterior</span>}
    {neighbors?.next ? <Link href={questionDetailHref(neighbors.next.id, filters)} className="flex min-h-14 min-w-0 flex-col items-end justify-center rounded-xl border border-slate-300 bg-white px-3 py-2 text-right text-sm font-semibold text-blue-700 hover:border-blue-400 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-300 sm:px-4">
      <span>Próxima →</span><span className="text-xs font-normal text-slate-600">Questão {neighbors.next.position}</span>
    </Link> : <span aria-disabled="true" className="flex min-h-14 items-center justify-end rounded-xl border border-slate-200 bg-slate-100 px-3 text-sm text-slate-500 sm:px-4">Próxima →</span>}
  </nav>;
}

export default function QuestionPage({ params }: { params: { id: string } }) {
  const [question, setQuestion] = useState<Question | null>(null);
  const [selected, setSelected] = useState("");
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState<QuestionFilters>(emptyQuestionFilters);
  const [neighbors, setNeighbors] = useState<Neighbors | null>(null);
  const [navigationError, setNavigationError] = useState(false);

  useEffect(() => {
    let active = true;
    const currentFilters = readQuestionFilters(window.location.search);
    setFilters(currentFilters);
    setQuestion(null);
    setSelected("");
    setResult(null);
    setNeighbors(null);
    setNavigationError(false);
    setError("");
    setLoading(true);
    api<Question>(`/questions/${encodeURIComponent(params.id)}`)
      .then((data) => { if (active) setQuestion(data); })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Não foi possível carregar a questão."); })
      .finally(() => { if (active) setLoading(false); });
    api<Neighbors>(`/questions/${encodeURIComponent(params.id)}/neighbors${questionFilterQuery(currentFilters, false)}`)
      .then((data) => { if (active) setNeighbors(data); })
      .catch(() => { if (active) setNavigationError(true); });
    return () => { active = false; };
  }, [params.id]);

  async function checkAnswer() {
    if (!question || !selected || checking) return;
    setChecking(true);
    setError("");
    try {
      const data = await api<AnswerResult>(`/questions/${encodeURIComponent(question.id)}/check`, {
        method: "POST", body: JSON.stringify({ answer: selected }),
      });
      setResult(data);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Não foi possível conferir a resposta.");
    } finally {
      setChecking(false);
    }
  }

  return <div className="mx-auto min-w-0 max-w-4xl space-y-4 pb-8 sm:space-y-5">
    <Link href={questionCatalogHref(filters)} className="inline-flex min-h-11 items-center text-sm font-semibold text-blue-700 hover:underline">← Voltar ao banco de questões</Link>
    {loading && <div role="status" className="rounded-xl border border-slate-200 bg-white p-8 text-slate-600">Carregando questão. O servidor gratuito pode levar cerca de um minuto para iniciar.</div>}
    {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>}
    {question && <>
      <header className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-7">
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">ENEM {question.year} · Dia {question.day} · {question.area_name}</p>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">Questão {question.position}</h1>
        <p className="mt-2 text-sm text-slate-600">{question.subject || "Disciplina ainda não classificada"} · Dificuldade TRI {difficultyLabels[question.difficulty].toLowerCase()}</p>
        {question.subject_classification === "automatic" && <p className="mt-2 text-xs text-slate-500">Disciplina sugerida automaticamente a partir do enunciado.</p>}
        {question.content_available && <p className="mt-2 text-xs leading-relaxed text-slate-500">Item TRI do caderno {question.booklet_color}, questão {question.position}. Transcrição: {question.source_booklet}, questão {question.source_position}. As letras e o gabarito seguem as alternativas exibidas abaixo.</p>}
      </header>
      <QuestionNavigation neighbors={neighbors} filters={filters} label="Navegar entre questões, início" />
      {navigationError && <p role="status" className="text-sm text-slate-600">Não foi possível carregar as setas de navegação. Você ainda pode voltar ao banco de questões.</p>}

      {question.content_available && question.blocks && question.alternatives ? <>
        <section className="space-y-5 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:space-y-6 sm:p-7" aria-label="Enunciado da questão">
          <h2 className="text-lg font-bold text-slate-900">Enunciado</h2>
          {question.blocks.map((block, index) => block.type === "image" ?
            <figure key={index} className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50 p-2 sm:p-4">
              <img src={block.value} alt={block.alt || `Figura da questão ${question.position}`} className="mx-auto max-h-[34rem] max-w-full object-contain" loading="lazy" />
              {block.alt && <figcaption className="mt-2 text-center text-xs text-slate-500">{block.alt}</figcaption>}
            </figure> : <p key={index} className="whitespace-pre-wrap break-words leading-7 text-slate-800">{block.value.replace(/^#{1,4}\s+/gm, "")}</p>)}
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-7" aria-label="Responder à questão">
          <h2 className="text-lg font-bold text-slate-900">Escolha uma alternativa</h2>
          <fieldset className="mt-5 space-y-3">
            <legend className="sr-only">Alternativas da questão {question.position}</legend>
            {question.alternatives.map((alternative) => <label key={alternative.letter} className={`flex min-h-16 min-w-0 cursor-pointer items-start gap-3 rounded-xl border-2 p-3 transition-colors focus-within:ring-2 focus-within:ring-blue-300 sm:gap-4 sm:p-4 ${selected === alternative.letter ? "border-blue-700 bg-blue-50" : "border-slate-200 bg-white hover:border-blue-300"}`}>
              <input type="radio" name="answer" value={alternative.letter} checked={selected === alternative.letter} onChange={() => { setSelected(alternative.letter); setResult(null); }} className="sr-only" />
              <span aria-hidden="true" className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-sm font-bold ${selected === alternative.letter ? "border-blue-700 bg-blue-700 text-white" : "border-slate-300 text-slate-700"}`}>{alternative.letter}</span>
              <span className="min-w-0 flex-1 space-y-3 pt-1 text-slate-800">
                {alternative.text && <span className="block whitespace-pre-wrap break-words leading-6">{alternative.text}</span>}
                {alternative.image && <img src={alternative.image} alt={`Imagem da alternativa ${alternative.letter}`} className="max-h-64 max-w-full object-contain" loading="lazy" />}
              </span>
            </label>)}
          </fieldset>
          <button type="button" onClick={checkAnswer} disabled={!selected || checking || !!result} className="mt-5 min-h-11 w-full rounded-lg bg-blue-700 px-6 font-semibold text-white hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto">{checking ? "Conferindo…" : "Conferir resposta"}</button>
          {result && <div role="status" aria-live="polite" className={`mt-4 rounded-xl border p-4 text-sm font-medium ${result.annulled ? "border-amber-200 bg-amber-50 text-amber-900" : result.correct ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-rose-200 bg-rose-50 text-rose-900"}`}>
            {result.annulled ? "Esta questão foi anulada no gabarito." : result.correct ? `Correto! A alternativa ${result.correct_answer} é a resposta do gabarito.` : `Sua resposta foi ${result.selected_answer}. O gabarito indica a alternativa ${result.correct_answer}.`}
          </div>}
        </section>
        <p className="text-xs text-slate-500">Texto e figuras: {question.content_source}. Confira a transcrição em caso de símbolos ou diagramas complexos.</p>
      </> : <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">O conteúdo desta questão ainda está em revisão. Ela permanece no catálogo TRI, mas não pode ser respondida aqui até que enunciado e alternativas sejam conferidos.</div>}
      <QuestionNavigation neighbors={neighbors} filters={filters} label="Navegar entre questões, fim" />
    </>}
  </div>;
}
