"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { QuestionPaper } from "@/components/QuestionPaper";
import { api } from "@/lib/api";

type Question = {
  id: string;
  year: number;
  day: number;
  area_name: string;
  subject: string | null;
  position: number;
  booklet_color: string;
  difficulty: "facil" | "media" | "dificil";
  paper_url: string | null;
  paper_page: number | null;
};

type AnswerResult = {
  selected_answer: string;
  correct_answer: string | null;
  correct: boolean | null;
  annulled: boolean;
};

const alternatives = ["A", "B", "C", "D", "E"];
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

  return <div className="mx-auto max-w-6xl space-y-5">
    <Link href="/questions" className="inline-flex min-h-11 items-center text-sm font-semibold text-blue-700 hover:underline">← Voltar ao banco de questões</Link>
    {loading && <div role="status" className="rounded-xl border border-slate-200 bg-white p-8 text-slate-600">Carregando questão. O servidor gratuito pode levar cerca de um minuto para iniciar.</div>}
    {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>}
    {question && <>
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">ENEM {question.year} · Dia {question.day} · {question.area_name}</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-slate-900">Questão {question.position}</h1>
          <p className="mt-1 text-sm text-slate-600">{question.subject || "Disciplina ainda não classificada"} · Caderno {question.booklet_color} · Dificuldade TRI {difficultyLabels[question.difficulty].toLowerCase()}</p>
        </div>
        {question.paper_url && <a href={`${question.paper_url}${question.paper_page ? `#page=${question.paper_page}` : ""}`} target="_blank" rel="noopener noreferrer" className="text-sm font-medium text-blue-700 underline">PDF oficial ↗</a>}
      </header>
      {question.paper_url && question.paper_page ? <QuestionPaper key={question.id} url={question.paper_url} initialPage={question.paper_page} questionNumber={question.position} /> :
        <div role="alert" className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">A página oficial desta questão não está mapeada. {question.paper_url && <a href={question.paper_url} target="_blank" rel="noopener noreferrer" className="underline">Abrir o caderno completo</a>}</div>}
      {question.paper_url && question.paper_page && <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" aria-label="Responder à questão">
        <h2 className="text-xl font-bold text-slate-900">Sua resposta</h2>
        <p className="mt-1 text-sm text-slate-600">Leia as alternativas A a E na página acima e marque uma opção.</p>
        <div role="radiogroup" aria-label="Alternativas" className="mt-4 grid grid-cols-5 gap-2 sm:max-w-xl">
          {alternatives.map((letter) => <label key={letter} className={`flex min-h-14 cursor-pointer items-center justify-center rounded-xl border-2 text-lg font-bold transition-colors focus-within:ring-2 focus-within:ring-blue-300 ${selected === letter ? "border-blue-700 bg-blue-50 text-blue-800" : "border-slate-200 bg-white text-slate-700 hover:border-blue-300"}`}>
            <input type="radio" name="answer" value={letter} checked={selected === letter} onChange={() => { setSelected(letter); setResult(null); }} className="sr-only" />{letter}
          </label>)}
        </div>
        <button type="button" onClick={checkAnswer} disabled={!selected || checking || !!result} className="mt-5 min-h-11 rounded-lg bg-blue-700 px-6 font-semibold text-white hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-50">{checking ? "Conferindo…" : "Conferir resposta"}</button>
        {result && <div role="status" aria-live="polite" className={`mt-4 rounded-xl border p-4 text-sm font-medium ${result.annulled ? "border-amber-200 bg-amber-50 text-amber-900" : result.correct ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-rose-200 bg-rose-50 text-rose-900"}`}>
          {result.annulled ? "Esta questão foi anulada no gabarito." : result.correct ? `Correto! A alternativa ${result.correct_answer} é a resposta do gabarito.` : `Sua resposta foi ${result.selected_answer}. O gabarito indica a alternativa ${result.correct_answer}.`}
        </div>}
      </section>}
    </>}
  </div>;
}
