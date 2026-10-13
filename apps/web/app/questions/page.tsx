"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

type Question = {
  id: string;
  year: number;
  day: number;
  area: string;
  area_name: string;
  subject: string | null;
  position: number;
  booklet_color: string;
  booklet_language: string | null;
  official_item_code: string | null;
  skill_code: string | null;
  difficulty: "facil" | "media" | "dificil";
  parameter_b: number;
  paper_url: string | null;
  paper_page: number | null;
};

type Catalog = {
  items: Question[];
  total: number;
  page: number;
  page_size: number;
  years: number[];
  subjects: string[];
  classified_count: number;
  analyzed_count: number;
  difficulty_note: string;
};

const areas = [
  { value: "LC", label: "Linguagens" },
  { value: "CH", label: "Ciências Humanas" },
  { value: "CN", label: "Ciências da Natureza" },
  { value: "MT", label: "Matemática" },
];

const difficultyLabels = { facil: "Fácil", media: "Média", dificil: "Difícil" };
const difficultyStyles = {
  facil: "bg-emerald-50 text-emerald-800 border-emerald-200",
  media: "bg-amber-50 text-amber-800 border-amber-200",
  dificil: "bg-rose-50 text-rose-800 border-rose-200",
};

export default function QuestionsPage() {
  const [year, setYear] = useState("");
  const [area, setArea] = useState("");
  const [subject, setSubject] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [page, setPage] = useState(1);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const params = new URLSearchParams({ page: String(page), page_size: "24" });
    if (year) params.set("year", year);
    if (area) params.set("area", area);
    if (subject) params.set("subject", subject);
    if (difficulty) params.set("difficulty", difficulty);
    setLoading(true);
    setError("");
    api<Catalog>(`/questions?${params}`)
      .then((data) => { if (active) setCatalog(data); })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Não foi possível carregar as questões."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [year, area, subject, difficulty, page]);

  const totalPages = catalog ? Math.ceil(catalog.total / catalog.page_size) : 0;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="space-y-3">
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">Acervo ENEM</p>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">Banco de questões TRI</h1>
        <p className="max-w-3xl text-slate-600">Explore questões com parâmetros publicados nos microdados do Inep. Leia a página oficial aqui no site, marque uma alternativa e confira sua resposta.</p>
      </header>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6" aria-label="Filtros de questões">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Encontre uma questão</h2>
            <p className="text-sm text-slate-500">Combine ano, área, disciplina e dificuldade.</p>
          </div>
          {catalog && <span className="text-sm font-medium text-slate-600">{catalog.total.toLocaleString("pt-BR")} questões encontradas</span>}
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="space-y-1 text-sm font-medium text-slate-700">Ano
            <select value={year} onChange={(event) => { setYear(event.target.value); setPage(1); }} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-slate-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-200">
              <option value="">Todos os anos</option>
              {catalog?.years.map((value) => <option value={value} key={value}>{value}</option>)}
            </select>
          </label>
          <label className="space-y-1 text-sm font-medium text-slate-700">Área
            <select value={area} onChange={(event) => { setArea(event.target.value); setPage(1); }} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-slate-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-200">
              <option value="">Todas as áreas</option>
              {areas.map((value) => <option value={value.value} key={value.value}>{value.label}</option>)}
            </select>
          </label>
          <label className="space-y-1 text-sm font-medium text-slate-700">Disciplina
            <select value={subject} onChange={(event) => { setSubject(event.target.value); setPage(1); }} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-slate-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-200">
              <option value="">Todas as disciplinas</option>
              {catalog?.subjects.map((value) => <option value={value} key={value}>{value}</option>)}
            </select>
          </label>
          <label className="space-y-1 text-sm font-medium text-slate-700">Dificuldade TRI
            <select value={difficulty} onChange={(event) => { setDifficulty(event.target.value); setPage(1); }} className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-slate-900 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-200">
              <option value="">Todas as dificuldades</option>
              <option value="facil">Fácil</option>
              <option value="media">Média</option>
              <option value="dificil">Difícil</option>
            </select>
          </label>
        </div>
        {catalog && <p className="mt-4 text-xs leading-relaxed text-slate-600">{catalog.difficulty_note} A classificação por disciplina está disponível para {catalog.classified_count.toLocaleString("pt-BR")} de {catalog.analyzed_count.toLocaleString("pt-BR")} itens; as demais questões permanecem sem disciplina até revisão do conteúdo.</p>}
      </section>

      {error && <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>}
      {loading && <div role="status" className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-600">Carregando questões. Se o servidor gratuito estiver iniciando, isso pode levar cerca de um minuto.</div>}
      {!loading && !error && catalog?.items.length === 0 && <div className="rounded-xl border border-slate-200 bg-white p-8 text-center text-slate-600">Nenhuma questão corresponde a esses filtros.</div>}

      {!loading && !error && catalog && catalog.items.length > 0 && <>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {catalog.items.map((question) => <article key={question.id} className="flex flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">ENEM {question.year} · Dia {question.day} · {question.area_name}</p>
                <h2 className="mt-1 text-xl font-bold text-slate-900">Questão {question.position}</h2>
              </div>
              <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${difficultyStyles[question.difficulty]}`}>{difficultyLabels[question.difficulty]}</span>
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
              <div><dt className="text-slate-500">Disciplina</dt><dd className="font-medium text-slate-800">{question.subject || "Não classificada"}</dd></div>
              <div><dt className="text-slate-500">Caderno</dt><dd className="font-medium text-slate-800">{question.booklet_color}{question.booklet_language && question.position <= 5 ? ` · ${question.booklet_language === "INGLES" ? "Inglês" : "Espanhol"}` : ""}</dd></div>
              <div><dt className="text-slate-500">Parâmetro b</dt><dd className="font-medium text-slate-800">{question.parameter_b.toLocaleString("pt-BR", { maximumFractionDigits: 4 })}</dd></div>
              <div><dt className="text-slate-500">Habilidade</dt><dd className="font-medium text-slate-800">{question.skill_code || "Não informada"}</dd></div>
            </dl>
            <div className="mt-auto pt-5">
              {question.paper_url && question.paper_page ? <Link href={`/questions/${question.id}`} className="inline-flex min-h-11 w-full items-center justify-center rounded-lg bg-blue-700 px-4 py-2 font-semibold text-white hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-300">Ler e responder</Link> : <p className="text-sm text-slate-500">Caderno oficial indisponível para esta questão.</p>}
            </div>
          </article>)}
        </div>
        <nav className="flex items-center justify-between gap-4" aria-label="Paginação de questões">
          <button type="button" onClick={() => setPage((value) => value - 1)} disabled={page <= 1} className="min-h-11 rounded-lg border border-slate-300 bg-white px-4 font-medium text-slate-700 disabled:cursor-not-allowed disabled:opacity-50">Anterior</button>
          <span className="text-center text-sm text-slate-600">Página {page} de {totalPages}</span>
          <button type="button" onClick={() => setPage((value) => value + 1)} disabled={page >= totalPages} className="min-h-11 rounded-lg border border-slate-300 bg-white px-4 font-medium text-slate-700 disabled:cursor-not-allowed disabled:opacity-50">Próxima</button>
        </nav>
      </>}
    </div>
  );
}
