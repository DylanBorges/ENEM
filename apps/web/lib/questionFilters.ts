export type QuestionFilters = {
  year: string;
  area: string;
  subject: string;
  difficulty: string;
  page: number;
};

export const emptyQuestionFilters: QuestionFilters = {
  year: "", area: "", subject: "", difficulty: "", page: 1,
};

export function readQuestionFilters(search: string): QuestionFilters {
  const params = new URLSearchParams(search);
  const page = Number(params.get("page"));
  const area = params.get("area") || "";
  const difficulty = params.get("difficulty") || "";
  const year = params.get("year") || "";
  return {
    year: /^\d{4}$/.test(year) ? year : "",
    area: ["LC", "CH", "CN", "MT"].includes(area) ? area : "",
    subject: params.get("subject") || "",
    difficulty: ["facil", "media", "dificil"].includes(difficulty) ? difficulty : "",
    page: Number.isSafeInteger(page) && page > 0 ? page : 1,
  };
}

export function questionFilterQuery(filters: QuestionFilters, includePage = true): string {
  const params = new URLSearchParams();
  if (filters.year) params.set("year", filters.year);
  if (filters.area) params.set("area", filters.area);
  if (filters.subject) params.set("subject", filters.subject);
  if (filters.difficulty) params.set("difficulty", filters.difficulty);
  if (includePage && filters.page > 1) params.set("page", String(filters.page));
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function questionCatalogHref(filters: QuestionFilters): string {
  return `/questions${questionFilterQuery(filters)}`;
}

export function questionDetailHref(id: string, filters: QuestionFilters): string {
  return `/questions/${encodeURIComponent(id)}${questionFilterQuery(filters)}`;
}
