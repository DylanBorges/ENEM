"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

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
const difficultyLabels = { facil: "Fácil", media: "Média", dificil: "Difícil" };

export default function QuestionPage({ params }: { params: { id: string } }) {
  const [question, setQuestion] = useState<Question | null>(null);
  const [selected, setSelected] = useState("");
  const [result, setResult] = useState<AnswerResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    api<Question>(`/questions/${encodeURIComponent(params.id)}`)
      .then((data) => { if (active) setQuestion(data); })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Não foi possível carregar a questão."); })
      .finally(() => { if (active) setLoading(false); });
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

  return <div className="mx-auto max-w-4xl space-y-5 pb-8">
    <Link href="/questions" className="inline-flex min-h-11 items-center text-sm font-semibold text-blue-700 hover:underline">← Voltar ao banco de questões</Link>
    {loading && <div role="status" className="rounded-xl border border-slate-200 bg-white p-8 text-slate-600">Carregando questão. O servidor gratuito pode levar cerca de um minuto para iniciar.</div>}
    {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>}
    {question && <>
      <header className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">ENEM {question.year} · Dia {question.day} · {question.area_name}</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">Questão {question.position}</h1>
        <p className="mt-2 text-sm text-slate-600">{question.subject || "Disciplina ainda não classificada"} · Dificuldade TRI {difficultyLabels[question.difficulty].toLowerCase()}</p>
        {question.subject_classification === "automatic" && <p className="mt-2 text-xs text-slate-500">Disciplina sugerida automaticamente a partir do enunciado.</p>}
        {question.content_available && <p className="mt-2 text-xs leading-relaxed text-slate-500">Item TRI do caderno {question.booklet_color}, questão {question.position}. Transcrição: {question.source_booklet}, questão {question.source_position}. As letras e o gabarito seguem as alternativas exibidas abaixo.</p>}
      </header>

      {question.content_available && question.blocks && question.alternatives ? <>
        <section className="space-y-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7" aria-label="Enunciado da questão">
          <h2 className="text-lg font-bold text-slate-900">Enunciado</h2>
          {question.blocks.map((block, index) => block.type === "image" ?
            <figure key={index} className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50 p-2 sm:p-4">
              <img src={block.value} alt={block.alt || `Figura da questão ${question.position}`} className="mx-auto max-h-[34rem] max-w-full object-contain" loading="lazy" />
              {block.alt && <figcaption className="mt-2 text-center text-xs text-slate-500">{block.alt}</figcaption>}
            </figure> : <p key={index} className="whitespace-pre-wrap break-words leading-7 text-slate-800">{block.value.replace(/^#{1,4}\s+/gm, "")}</p>)}
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7" aria-label="Responder à questão">
          <h2 className="text-lg font-bold text-slate-900">Escolha uma alternativa</h2>
          <fieldset className="mt-5 space-y-3">
            <legend className="sr-only">Alternativas da questão {question.position}</legend>
            {question.alternatives.map((alternative) => <label key={alternative.letter} className={`flex min-h-16 cursor-pointer items-start gap-4 rounded-xl border-2 p-4 transition-colors focus-within:ring-2 focus-within:ring-blue-300 ${selected === alternative.letter ? "border-blue-700 bg-blue-50" : "border-slate-200 bg-white hover:border-blue-300"}`}>
              <input type="radio" name="answer" value={alternative.letter} checked={selected === alternative.letter} onChange={() => { setSelected(alternative.letter); setResult(null); }} className="sr-only" />
              <span aria-hidden="true" className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full border text-sm font-bold ${selected === alternative.letter ? "border-blue-700 bg-blue-700 text-white" : "border-slate-300 text-slate-700"}`}>{alternative.letter}</span>
              <span className="min-w-0 flex-1 space-y-3 pt-1 text-slate-800">
                {alternative.text && <span className="block whitespace-pre-wrap break-words leading-6">{alternative.text}</span>}
                {alternative.image && <img src={alternative.image} alt={`Imagem da alternativa ${alternative.letter}`} className="max-h-64 max-w-full object-contain" loading="lazy" />}
              </span>
            </label>)}
          </fieldset>
          <button type="button" onClick={checkAnswer} disabled={!selected || checking || !!result} className="mt-5 min-h-11 rounded-lg bg-blue-700 px-6 font-semibold text-white hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-50">{checking ? "Conferindo…" : "Conferir resposta"}</button>
          {result && <div role="status" aria-live="polite" className={`mt-4 rounded-xl border p-4 text-sm font-medium ${result.annulled ? "border-amber-200 bg-amber-50 text-amber-900" : result.correct ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-rose-200 bg-rose-50 text-rose-900"}`}>
            {result.annulled ? "Esta questão foi anulada no gabarito." : result.correct ? `Correto! A alternativa ${result.correct_answer} é a resposta do gabarito.` : `Sua resposta foi ${result.selected_answer}. O gabarito indica a alternativa ${result.correct_answer}.`}
          </div>}
        </section>
        <p className="text-xs text-slate-500">Texto e figuras: {question.content_source}. Confira a transcrição em caso de símbolos ou diagramas complexos.</p>
      </> : <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900">O conteúdo desta questão ainda está em revisão. Ela permanece no catálogo TRI, mas não pode ser respondida aqui até que enunciado e alternativas sejam conferidos.</div>}
    </>}
  </div>;
}
